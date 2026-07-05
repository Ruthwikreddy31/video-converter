import subprocess
import json
import os
import math
import time
from typing import Optional, Dict, Any

from app.services.config import FFMPEG_BIN, FFPROBE_BIN, SUBPROCESS_FLAGS


def probe_video(file_path: str) -> Dict[str, Any]:
    """Use ffprobe to extract video metadata."""
    abs_path = os.path.abspath(file_path)
    if not os.path.exists(abs_path):
        raise ValueError(f"Video file not found: {abs_path}")

    cmd = [
        FFPROBE_BIN,
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        abs_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, **SUBPROCESS_FLAGS)
    if result.returncode != 0:
        raise ValueError(f"FFprobe failed: {result.stderr or result.stdout}")
    return json.loads(result.stdout)


def extract_video_info(file_path: str) -> Dict[str, Any]:
    """Extract comprehensive video information."""
    data = probe_video(file_path)

    video_stream = None
    audio_stream = None

    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video" and video_stream is None:
            video_stream = stream
        elif stream.get("codec_type") == "audio" and audio_stream is None:
            audio_stream = stream

    if not video_stream:
        raise ValueError("No video stream found in file")

    width = int(video_stream.get("width", 0))
    height = int(video_stream.get("height", 0))

    fps_str = video_stream.get("r_frame_rate", "24/1")
    fps_parts = fps_str.split("/")
    fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 and float(fps_parts[1]) != 0 else 24.0

    duration = float(data.get("format", {}).get("duration", 0) or 0)
    if not duration and "duration" in video_stream:
        duration = float(video_stream["duration"] or 0)

    file_size = 0
    try:
        file_size = int(data.get("format", {}).get("size", 0) or 0)
        if not file_size:
            file_size = os.path.getsize(os.path.abspath(file_path))
    except Exception:
        pass

    gcd = math.gcd(width, height) if width and height else 1
    # Use higher precision internally for crop math; round only for display
    ar_precise = width / height if height > 0 else 0
    ar_decimal = round(ar_precise, 2)
    detected_format = detect_format_name(ar_precise)

    return {
        "width": width,
        "height": height,
        "duration": round(duration, 2),
        "fps": round(fps, 2),
        "file_size": file_size,
        "aspect_ratio": f"{width // gcd}:{height // gcd}",
        "aspect_ratio_decimal": ar_decimal,
        "detected_format": detected_format,
        "video_codec": video_stream.get("codec_name", "unknown"),
        "audio_codec": audio_stream.get("codec_name", "none") if audio_stream else "none",
        "pixel_format": video_stream.get("pix_fmt", "unknown"),
        "bitrate": int(data.get("format", {}).get("bit_rate", 0) or 0),
    }


def detect_format_name(ar: float) -> str:
    """
    Detect the cinematic format name from a precise (unrounded) aspect ratio.

    Tolerances are intentionally tight (±0.02-0.03) so that videos which are
    merely *close* to a named cinema ratio (e.g. a 1.39:1 clip) are NOT
    mislabeled as that format. Anything that doesn't clearly match a known
    standard falls through to "Custom (x.xx:1)".
    """
    if abs(ar - 2.39) < 0.03:
        return "Scope (2.39:1)"
    if abs(ar - 2.35) < 0.03:
        return "Scope (2.35:1)"
    if abs(ar - 2.76) < 0.03:
        return "Ultra Panavision (2.76:1)"
    if abs(ar - 1.90) < 0.03:
        return "Digital IMAX (1.90:1)"
    if abs(ar - 1.85) < 0.02:
        return "Widescreen (1.85:1)"
    if abs(ar - 1.78) < 0.02 or abs(ar - 1.777) < 0.015:
        return "Standard Widescreen (16:9)"
    if abs(ar - 1.43) < 0.02:
        return "Full IMAX (1.43:1)"
    if abs(ar - 1.33) < 0.02 or abs(ar - 4/3) < 0.02:
        return "Academy / 4:3 (1.33:1)"
    if abs(ar - 1.0) < 0.02:
        return "Square (1:1)"
    if ar > 2.5:
        return f"Ultra Wide ({ar:.2f}:1)"
    if ar < 1.0:
        return f"Portrait ({ar:.2f}:1)"
    return f"Custom ({ar:.2f}:1)"


def generate_thumbnail(video_path: str, output_path: str, timestamp: float = 3.0) -> bool:
    """Generate a thumbnail at a specific timestamp."""
    abs_input = os.path.abspath(video_path)
    abs_output = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(abs_output), exist_ok=True)

    cmd = [
        FFMPEG_BIN, "-y",
        "-ss", str(min(timestamp, 3.0)),
        "-i", abs_input,
        "-vframes", "1",
        "-q:v", "2",
        "-vf", "scale=640:-2",
        abs_output
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, **SUBPROCESS_FLAGS)
    return result.returncode == 0


def generate_preview_frame(video_path: str, output_path: str, crop_filter: str) -> bool:
    """Generate a preview frame with a specific crop/pad filter."""
    abs_input = os.path.abspath(video_path)
    abs_output = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(abs_output), exist_ok=True)

    cmd = [
        FFMPEG_BIN, "-y",
        "-ss", "3",
        "-i", abs_input,
        "-vframes", "1",
        "-vf", f"{crop_filter},scale=640:-2",
        "-q:v", "2",
        abs_output
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, **SUBPROCESS_FLAGS)
    return result.returncode == 0


def get_crop_filter_for_format(width: int, height: int, target_ratio: float) -> Dict[str, Any]:
    """
    Calculate a CROP filter to reach target_ratio.
    Only valid when current_ratio > target_ratio (source is wider than target,
    so we crop top/bottom) — see build_pad_filter for the opposite case.
    """
    current_ratio = width / height

    if current_ratio > target_ratio:
        # Source wider than target -> crop the SIDES (reduce width)
        new_width = int(round(height * target_ratio))
        new_width = new_width if new_width % 2 == 0 else new_width - 1
        new_width = max(2, min(new_width, width))
        x_offset = max(0, (width - new_width) // 2)
        return {
            "filter": f"crop={new_width}:{height}:{x_offset}:0",
            "method": "horizontal_crop",
            "output_width": new_width,
            "output_height": height,
        }
    else:
        # Source taller/narrower than target -> crop TOP/BOTTOM (reduce height)
        new_height = int(round(width / target_ratio))
        new_height = new_height if new_height % 2 == 0 else new_height - 1
        new_height = max(2, min(new_height, height))
        y_offset = max(0, (height - new_height) // 2)
        return {
            "filter": f"crop={width}:{new_height}:0:{y_offset}",
            "method": "vertical_crop",
            "output_width": width,
            "output_height": new_height,
        }


def build_pad_filter(width: int, height: int, target_ratio: float) -> Dict[str, Any]:
    """
    Calculate a PAD filter to reach target_ratio.

    Only called when current_ratio < target_ratio — i.e. the source is
    TALLER (narrower) than the target, so we must ADD WIDTH (pillarbox),
    not change the height. (Padding height in this case would require a
    *negative* offset and crash FFmpeg — this was the original bug.)
    """
    current_ratio = width / height

    if current_ratio >= target_ratio:
        # Defensive fallback — shouldn't normally be called in this branch,
        # but if it is, there's nothing to pad; return a no-op-ish crop.
        return get_crop_filter_for_format(width, height, target_ratio)

    # Need to widen the frame: new_width = height * target_ratio
    new_width = int(round(height * target_ratio))
    new_width = new_width if new_width % 2 == 0 else new_width + 1  # round UP, never shrink
    x_offset = max(0, (new_width - width) // 2)

    return {
        "filter": f"pad={new_width}:{height}:{x_offset}:0:black",
        "method": "pad",
        "output_width": new_width,
        "output_height": height,
    }


def build_smart_crop_filter(coords: Dict, width: int, height: int, target_ratio: float) -> str:
    """Build a crop filter centered on detected subjects (face/person)."""
    subject_cx = coords.get("center_x", width // 2)
    subject_cy = coords.get("center_y", height // 2)
    current_ratio = width / height

    if current_ratio > target_ratio:
        new_width = int(round(height * target_ratio))
        new_width = new_width if new_width % 2 == 0 else new_width - 1
        new_width = max(2, min(new_width, width))
        x_offset = max(0, min(subject_cx - new_width // 2, width - new_width))
        return f"crop={new_width}:{height}:{x_offset}:0"
    else:
        new_height = int(round(width / target_ratio))
        new_height = new_height if new_height % 2 == 0 else new_height - 1
        new_height = max(2, min(new_height, height))
        y_offset = max(0, min(subject_cy - new_height // 2, height - new_height))
        return f"crop={width}:{new_height}:0:{y_offset}"


def convert_video(
    input_path: str,
    output_path: str,
    target_format: str,
    video_info: Dict[str, Any],
    crop_method: str = "center",
    smart_crop_coords: Optional[Dict] = None,
    progress_callback=None
) -> Dict[str, Any]:
    """Convert video to target aspect ratio format."""
    abs_input = os.path.abspath(input_path)
    abs_output = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(abs_output), exist_ok=True)

    width = video_info["width"]
    height = video_info["height"]
    target_ratios = {
        "scope": 2.39,
        "digital_imax": 1.90,
        "full_imax": 1.43,
        "imax_70mm": 1.43,
        "imax_digital": 1.90,
        "70mm_std": 2.20,
        "35mm_std": 2.39,
        "large_format": 1.85,
        "dolby_vision": 1.85,
    }
    is_border = target_format.endswith("_border")
    clean_format = target_format.replace("_border", "")
    target_ratio = target_ratios.get(clean_format)
    if not target_ratio:
        raise ValueError(f"Unknown target format: {target_format}")

    current_ratio = width / height

    # Full IMAX expansion check
    if not is_border and clean_format in ("full_imax", "imax_70mm") and current_ratio > 2.0:
        return {
            "success": False,
            "needs_ai_expansion": True,
            "message": (
                "True IMAX conversion requires additional vertical image data "
                "not present in the source. The source is too wide to crop "
                "down to 1.43:1 without losing most of the frame."
            ),
        }

    # Decide the filter.
    if is_border:
        crop_filter = build_pad_filter(width, height, target_ratio)["filter"]
    elif smart_crop_coords and crop_method == "smart":
        crop_filter = build_smart_crop_filter(smart_crop_coords, width, height, target_ratio)
    else:
        crop_filter = get_crop_filter_for_format(width, height, target_ratio)["filter"]

    video_codec = "libx264"
    pix_fmt = "yuv420p"
    color_args = []
    
    if clean_format == "dolby_vision":
        # High quality 10-bit HDR encoding for Dolby Vision simulation
        pix_fmt = "yuv420p10le"
        color_args = [
            "-colorspace", "bt2020nc",
            "-color_primaries", "bt2020",
            "-color_trc", "smpte2084",
            "-profile:v", "high10",
        ]

    cmd = [
        FFMPEG_BIN, "-y",
        "-i", abs_input,
        "-vf", crop_filter,
        "-c:v", video_codec,
        "-pix_fmt", pix_fmt,
        *color_args,
        "-crf", "16" if clean_format == "dolby_vision" else "18",
        "-preset", "medium",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        "-progress", "pipe:1",
        abs_output
    ]

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # CRITICAL: merge stderr into stdout.
        # FFmpeg writes its verbose logging (codec info, frame stats, etc.)
        # to stderr while -progress pipe:1 writes progress to stdout. With
        # them as TWO SEPARATE PIPEs, nobody was draining stderr — once
        # FFmpeg's normal logging filled the OS pipe buffer (~64KB), FFmpeg
        # blocked on write() and the whole conversion hung forever. This is
        # exactly the "stuck at 18%" bug: 18% is the moment this subprocess
        # starts. Merging into one stream means everything gets drained by
        # the same readline() loop below, so the buffer can never fill.
        text=True,
        bufsize=1,
        **SUBPROCESS_FLAGS
    )

    duration = video_info.get("duration", 0)
    output_lines: list = []
    last_progress_time = time.time()
    # Safety net: if FFmpeg produces literally zero output for this long,
    # something is wrong (hung process, corrupt input, etc.) — kill it
    # rather than waiting forever with no feedback at all.
    STALL_TIMEOUT_SECONDS = 120

    while True:
        line = process.stdout.readline()

        if not line:
            if process.poll() is not None:
                break
            if time.time() - last_progress_time > STALL_TIMEOUT_SECONDS:
                process.kill()
                process.wait()
                raise RuntimeError(
                    f"FFmpeg produced no output for over {STALL_TIMEOUT_SECONDS}s and was killed. "
                    f"This usually means a corrupt/unsupported input file, or FFmpeg itself is "
                    f"stuck. Filter used: {crop_filter}"
                )
            continue

        last_progress_time = time.time()
        line = line.strip()
        if line:
            output_lines.append(line)

        if line.startswith("out_time_ms=") and progress_callback:
            try:
                time_ms = int(line.split("=")[1].strip())
                if duration > 0:
                    progress_callback(min(int((time_ms / 1_000_000 / duration) * 100), 99))
            except Exception:
                pass

    process.wait()
    if process.returncode != 0:
        # Show the tail of FFmpeg's actual output — this is the real error
        # (corrupt file, unsupported codec, filter syntax issue, etc.)
        tail = "\n".join(output_lines[-25:]) if output_lines else "(no output captured)"
        raise RuntimeError(
            f"FFmpeg conversion failed (exit code {process.returncode}, filter: {crop_filter}):\n{tail}"
        )

    if progress_callback:
        progress_callback(100)

    return {"success": True, "output_path": abs_output, "crop_method": crop_method, "filter_used": crop_filter}
