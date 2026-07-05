import subprocess
import json
import os
import re
import sys
from typing import Optional, Dict, Any, Callable

from app.services.config import YTDLP_BIN, FFMPEG_BIN, SUBPROCESS_FLAGS

# Cap download resolution by default. Many trailers/promo videos are
# uploaded in 4K (or higher) masters — without a cap, yt-dlp's "best"
# selector grabs the absolute highest quality available, which for a 4K
# trailer can be several GB and take 30-60+ minutes even on a decent
# connection. Capping to 1080p (still excellent quality, more than enough
# for any of the cinema aspect-ratio crops this app produces) keeps
# downloads in a reasonable multi-minute range. Override via .env:
#   MAX_DOWNLOAD_HEIGHT=2160   (allow up to 4K)
#   MAX_DOWNLOAD_HEIGHT=0      (no cap — original "best" behavior)
MAX_DOWNLOAD_HEIGHT = int(os.getenv("MAX_DOWNLOAD_HEIGHT", "1080") or "1080")


def validate_youtube_url(url: str) -> bool:
    patterns = [
        r"^https?://(www\.)?youtube\.com/watch\?v=[\w-]+",
        r"^https?://youtu\.be/[\w-]+",
        r"^https?://(www\.)?youtube\.com/shorts/[\w-]+",
    ]
    return any(re.match(p, url) for p in patterns)


def _clean_url(url: str) -> str:
    """
    Strip tracking params (?si=...) that are sometimes mangled by clients
    and can occasionally cause yt-dlp extraction quirks. Keep only the
    core video id parameter.
    """
    url = url.strip()
    # youtu.be/<id>?si=xxx  -> youtu.be/<id>
    m = re.match(r"^(https?://youtu\.be/[\w-]+)", url)
    if m:
        return m.group(1)
    # youtube.com/watch?v=<id>&...  -> youtube.com/watch?v=<id>
    m = re.match(r"^(https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+)", url)
    if m:
        return m.group(1)
    # youtube.com/shorts/<id>?...  -> youtube.com/shorts/<id>
    m = re.match(r"^(https?://(?:www\.)?youtube\.com/shorts/[\w-]+)", url)
    if m:
        return m.group(1)
    return url


def get_video_info(url: str) -> Dict[str, Any]:
    clean_url = _clean_url(url)
    cmd = [YTDLP_BIN, "--dump-json", "--no-playlist", "--no-warnings", clean_url]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, **SUBPROCESS_FLAGS)
    if result.returncode != 0:
        raise ValueError(_friendly_yt_error(result.stderr or result.stdout))
    data = json.loads(result.stdout)
    return {
        "title": data.get("title", "Unknown"),
        "duration": data.get("duration", 0),
        "thumbnail": data.get("thumbnail", ""),
        "uploader": data.get("uploader", "Unknown"),
        "view_count": data.get("view_count", 0),
        "id": data.get("id", ""),
    }


def _friendly_yt_error(raw_output: str) -> str:
    """Translate common yt-dlp error patterns into a clear, specific message."""
    err = (raw_output or "").lower()

    if "private" in err:
        return "This video is private and cannot be downloaded."
    if "age" in err and "restrict" in err:
        return "This video is age-restricted and cannot be downloaded without sign-in."
    if "unavailable" in err or "not available" in err:
        return "This video is unavailable (may be deleted, region-blocked, or removed)."
    if "sign in to confirm" in err or "not a bot" in err:
        return "YouTube is requiring sign-in verification for this video (bot check). Try a different video, or update yt-dlp: pip install -U yt-dlp"
    if "unable to extract" in err or "failed to extract" in err:
        return "YouTube changed something yt-dlp doesn't recognize yet. Run: pip install -U yt-dlp"
    if "certificate" in err or "ssl" in err:
        return "SSL/certificate error reaching YouTube. Check your network/firewall/antivirus SSL inspection settings."
    if "http error 429" in err or "too many requests" in err:
        return "YouTube is rate-limiting this connection. Wait a few minutes and try again."
    if "no video formats found" in err or "requested format is not available" in err:
        return "No downloadable format found for this video with the current settings."
    if "ffmpeg" in err and ("not found" in err or "is not installed" in err):
        return "yt-dlp could not find FFmpeg. Check FFMPEG_PATH in backend/.env."
    if "could not find a version that satisfies" in err or "command not found" in err or "is not recognized" in err:
        return "yt-dlp executable not found. Run: pip install yt-dlp"

    # Fall back to raw output (truncated) so nothing is ever silently hidden
    cleaned = raw_output.strip().replace("\n", " ")[:400] if raw_output else "Unknown error"
    return f"yt-dlp error: {cleaned}"


def _build_format_selector() -> str:
    """
    Build the yt-dlp -f selector, capped to MAX_DOWNLOAD_HEIGHT (default
    1080p) unless explicitly disabled via .env (MAX_DOWNLOAD_HEIGHT=0).
    Falls back broadly so something always downloads even if mp4-specific
    or height-capped streams aren't available for a given video.
    """
    if MAX_DOWNLOAD_HEIGHT and MAX_DOWNLOAD_HEIGHT > 0:
        h = MAX_DOWNLOAD_HEIGHT
        return (
            f"bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]/"
            f"bestvideo[height<={h}]+bestaudio/"
            f"best[height<={h}]/"
            f"bestvideo[ext=mp4]+bestaudio[ext=m4a]/"
            f"bestvideo+bestaudio/best"
        )
    # No cap — original "grab the absolute best" behavior
    return "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best/bestvideo*+bestaudio/best"


def download_video(
    url: str,
    output_dir: str,
    video_id: str,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> str:
    abs_dir = os.path.abspath(output_dir)
    os.makedirs(abs_dir, exist_ok=True)

    clean_url = _clean_url(url)
    output_template = os.path.join(abs_dir, f"{video_id}.%(ext)s")
    final_mp4 = os.path.join(abs_dir, f"{video_id}.mp4")

    # Tell yt-dlp exactly where ffmpeg.exe lives (critical on Windows)
    ffmpeg_dir = os.path.dirname(os.path.abspath(FFMPEG_BIN))

    format_selector = _build_format_selector()

    cmd = [
        YTDLP_BIN,
        "--no-playlist",
        "--no-warnings",
        "-f", format_selector,
        "--merge-output-format", "mp4",
        "--ffmpeg-location", ffmpeg_dir,
        "-o", output_template,
        "--newline",
        "--progress",
        "--no-check-certificate",   # tolerate SSL-inspecting proxies/antivirus
        clean_url,
    ]

    popen_flags = {k: v for k, v in SUBPROCESS_FLAGS.items() if k != "creationflags"}

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        **popen_flags
    )

    tracked_file = None
    full_output_lines = []   # capture EVERYTHING so failures are never silent

    for line in process.stdout:
        line = line.strip()
        if not line:
            continue
        full_output_lines.append(line)

        if "[download]" in line and "%" in line:
            m = re.search(r"(\d+\.?\d*)%", line)
            if m and progress_callback:
                progress_callback(int(float(m.group(1))), f"Downloading... {m.group(1)}%")

        if "Destination:" in line:
            m = re.search(r"Destination:\s*(.+)", line)
            if m:
                c = m.group(1).strip()
                if c.lower().endswith(".mp4"):
                    tracked_file = c

        if "[Merger]" in line:
            m = re.search(r'Merging formats into "(.+?)"', line)
            if m:
                tracked_file = m.group(1).strip()

        if "[download] 100%" in line and progress_callback:
            progress_callback(100, "Processing...")

    process.wait()

    full_output = "\n".join(full_output_lines)

    if process.returncode != 0:
        # Surface the REAL error instead of a generic message
        raise RuntimeError(_friendly_yt_error(full_output))

    for candidate in [tracked_file, final_mp4]:
        if candidate and os.path.isfile(candidate):
            return candidate

    for fname in sorted(os.listdir(abs_dir)):
        if fname.startswith(video_id):
            full = os.path.join(abs_dir, fname)
            if os.path.isfile(full):
                return full

    # Even on returncode==0, if no file appeared, show the tail of yt-dlp's
    # own output — this is the actual information needed to debug it
    tail = "\n".join(full_output_lines[-15:]) if full_output_lines else "(no output captured)"
    raise RuntimeError(
        f"yt-dlp reported success but no output file was found in {abs_dir}.\n"
        f"Last yt-dlp output:\n{tail}"
    )
