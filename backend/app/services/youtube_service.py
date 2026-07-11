import subprocess
import json
import os
import re
from typing import Optional, Dict, Any, Callable

from app.services.config import YTDLP_BIN, FFMPEG_BIN, SUBPROCESS_FLAGS

MAX_DOWNLOAD_HEIGHT = int(os.getenv("MAX_DOWNLOAD_HEIGHT", "720") or "720")


def _resolve_cookies_file() -> str:
    from_env = os.getenv("YOUTUBE_COOKIES_FILE", "").strip()
    if from_env and os.path.isfile(from_env):
        print(f"[youtube] Using cookies: {from_env}")
        return from_env

    candidates = [
        "/etc/secrets/cookies.txt",
        os.path.join(os.path.dirname(__file__), "..", "..", "cookies", "cookies.txt"),
        os.path.join(os.getcwd(), "cookies", "cookies.txt"),
        "/app/cookies/cookies.txt",
    ]
    for c in candidates:
        abs_c = os.path.abspath(c)
        if os.path.isfile(abs_c):
            print(f"[youtube] Found cookies at: {abs_c}")
            return abs_c

    print("[youtube] WARNING: No cookies.txt found.")
    return ""


COOKIES_FILE = _resolve_cookies_file()


def validate_youtube_url(url: str) -> bool:
    patterns = [
        r"^https?://(www\.)?youtube\.com/watch\?v=[\w-]+",
        r"^https?://youtu\.be/[\w-]+",
        r"^https?://(www\.)?youtube\.com/shorts/[\w-]+",
    ]
    return any(re.match(p, url) for p in patterns)


def _clean_url(url: str) -> str:
    url = url.strip()
    m = re.match(r"^(https?://youtu\.be/[\w-]+)", url)
    if m: return m.group(1)
    m = re.match(r"^(https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+)", url)
    if m: return m.group(1)
    m = re.match(r"^(https?://(?:www\.)?youtube\.com/shorts/[\w-]+)", url)
    if m: return m.group(1)
    return url


def _cookies_args() -> list:
    cookies = COOKIES_FILE or _resolve_cookies_file()
    if cookies and os.path.isfile(cookies):
        return ["--cookies", cookies]
    return []


def _base_ytdlp_args() -> list:
    """
    Core yt-dlp arguments that bypass YouTube's bot detection and 403 errors.

    HTTP 403 Forbidden on video data happens when:
    1. YouTube ties the session cookie to the original browser's IP
    2. The download comes from a different IP (Render server)
    3. YouTube detects the mismatch and blocks the stream

    Fix: use the Android or iOS client instead of the web client.
    These clients use different authentication that isn't IP-tied.
    --extractor-args "youtube:player_client=android"
    tells yt-dlp to fetch the video using YouTube's Android API,
    which is far less strictly validated against IP.
    """
    return [
        "--extractor-args", "youtube:player_client=android,web",
        "--no-check-certificate",
        "--socket-timeout", "30",
        "--retries", "3",
        "--fragment-retries", "3",
    ]


def get_video_info(url: str) -> Dict[str, Any]:
    clean_url = _clean_url(url)
    cmd = [
        YTDLP_BIN,
        "--dump-json",
        "--no-playlist",
        "--no-warnings",
        *_base_ytdlp_args(),
        *_cookies_args(),
        clean_url
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, **SUBPROCESS_FLAGS)
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
    err = (raw_output or "").lower()
    if "private" in err:
        return "This video is private and cannot be downloaded."
    if "age" in err and "restrict" in err:
        return "This video is age-restricted."
    if "unavailable" in err or "not available" in err:
        return "This video is unavailable (deleted, region-blocked, or removed)."
    if "sign in to confirm" in err or "not a bot" in err:
        return "YouTube bot check failed. Refresh your cookies.txt on Render."
    if "http error 403" in err or "forbidden" in err:
        return (
            "YouTube returned 403 Forbidden on the video stream. "
            "This usually means your cookies have expired or are IP-restricted. "
            "Please re-export fresh cookies from your browser while logged into YouTube "
            "and update them in Render → Environment → Secret Files → cookies.txt"
        )
    if "http error 429" in err or "too many requests" in err:
        return "YouTube is rate-limiting this server. Wait a few minutes and try again."
    if "unable to extract" in err or "failed to extract" in err:
        return "yt-dlp needs updating. Contact admin to run: pip install -U yt-dlp"
    if "no video formats found" in err or "requested format is not available" in err:
        return "No downloadable format found for this video."
    if "no space left" in err or "disk" in err:
        return "Server ran out of disk space. Try again later."
    if "certificate" in err or "ssl" in err:
        return "SSL error reaching YouTube."
    cleaned = raw_output.strip().replace("\n", " ")[:500] if raw_output else "Unknown error"
    return f"yt-dlp error: {cleaned}"


def _build_format_selector() -> str:
    if MAX_DOWNLOAD_HEIGHT and MAX_DOWNLOAD_HEIGHT > 0:
        h = MAX_DOWNLOAD_HEIGHT
        return (
            f"bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]/"
            f"bestvideo[height<={h}]+bestaudio/"
            f"best[height<={h}]/"
            f"bestvideo[ext=mp4]+bestaudio[ext=m4a]/"
            f"bestvideo+bestaudio/best"
        )
    return "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"


def download_video(
    url: str,
    output_dir: str,
    video_id: str,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> str:
    abs_dir = os.path.abspath(output_dir)
    os.makedirs(abs_dir, exist_ok=True)

    # Check disk space
    try:
        import shutil
        free_mb = shutil.disk_usage(abs_dir).free / (1024 * 1024)
        print(f"[youtube] Available disk: {free_mb:.0f} MB")
        if free_mb < 150:
            raise RuntimeError(
                f"Only {free_mb:.0f}MB disk space left. Try again later."
            )
    except RuntimeError:
        raise
    except Exception:
        pass

    clean_url = _clean_url(url)
    output_template = os.path.join(abs_dir, f"{video_id}.%(ext)s")
    final_mp4 = os.path.join(abs_dir, f"{video_id}.mp4")
    ffmpeg_dir = os.path.dirname(os.path.abspath(FFMPEG_BIN))
    format_selector = _build_format_selector()
    cookies = _cookies_args()

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
        *_base_ytdlp_args(),   # android client + retry flags
        *cookies,
        clean_url,
    ]

    popen_flags = {k: v for k, v in SUBPROCESS_FLAGS.items() if k != "creationflags"}

    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1, **popen_flags
    )

    tracked_file = None
    full_output_lines = []

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
        raise RuntimeError(_friendly_yt_error(full_output))

    for candidate in [tracked_file, final_mp4]:
        if candidate and os.path.isfile(candidate):
            return candidate

    for fname in sorted(os.listdir(abs_dir)):
        if fname.startswith(video_id):
            fp = os.path.join(abs_dir, fname)
            if os.path.isfile(fp):
                return fp

    tail = "\n".join(full_output_lines[-15:]) if full_output_lines else "(no output)"
    raise RuntimeError(f"yt-dlp succeeded but no file found.\nLast output:\n{tail}")