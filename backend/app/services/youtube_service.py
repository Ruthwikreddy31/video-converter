import subprocess
import json
import os
import re
import sys
from typing import Optional, Dict, Any, Callable

from app.services.config import YTDLP_BIN, FFMPEG_BIN, SUBPROCESS_FLAGS

MAX_DOWNLOAD_HEIGHT = int(os.getenv("MAX_DOWNLOAD_HEIGHT", "1080") or "1080")

# Path to YouTube cookies file — fixes "Sign in to confirm you're not a bot"
# errors on cloud servers (Render, Railway, etc.) whose IPs are flagged.
# Set YOUTUBE_COOKIES_FILE=/app/cookies/cookies.txt in your Render env vars.
COOKIES_FILE = os.getenv("YOUTUBE_COOKIES_FILE", "")

# Fallback: auto-detect cookies.txt in common locations relative to this file
if not COOKIES_FILE:
    _candidates = [
        os.path.join(os.path.dirname(__file__), "..", "..", "cookies", "cookies.txt"),
        os.path.join(os.getcwd(), "cookies", "cookies.txt"),
        "/app/cookies/cookies.txt",
    ]
    for _c in _candidates:
        if os.path.isfile(_c):
            COOKIES_FILE = os.path.abspath(_c)
            print(f"[youtube] Auto-detected cookies file: {COOKIES_FILE}")
            break


def validate_youtube_url(url: str) -> bool:
    patterns = [
        r"^https?://(www\.)?youtube\.com/watch\?v=[\w-]+",
        r"^https?://youtu\.be/[\w-]+",
        r"^https?://(www\.)?youtube\.com/shorts/[\w-]+",
    ]
    return any(re.match(p, url) for p in patterns)


def _clean_url(url: str) -> str:
    """Strip tracking params (?si=...) that can cause yt-dlp extraction quirks."""
    url = url.strip()
    m = re.match(r"^(https?://youtu\.be/[\w-]+)", url)
    if m: return m.group(1)
    m = re.match(r"^(https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+)", url)
    if m: return m.group(1)
    m = re.match(r"^(https?://(?:www\.)?youtube\.com/shorts/[\w-]+)", url)
    if m: return m.group(1)
    return url


def _cookies_args() -> list:
    """Return yt-dlp cookie arguments if a cookies file is available."""
    if COOKIES_FILE and os.path.isfile(COOKIES_FILE):
        return ["--cookies", COOKIES_FILE]
    return []


def get_video_info(url: str) -> Dict[str, Any]:
    clean_url = _clean_url(url)
    cmd = [
        YTDLP_BIN,
        "--dump-json",
        "--no-playlist",
        "--no-warnings",
        *_cookies_args(),
        clean_url
    ]
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
    """Translate common yt-dlp error patterns into clear, specific messages."""
    err = (raw_output or "").lower()

    if "private" in err:
        return "This video is private and cannot be downloaded."
    if "age" in err and "restrict" in err:
        return "This video is age-restricted and cannot be downloaded without sign-in."
    if "unavailable" in err or "not available" in err:
        return "This video is unavailable (may be deleted, region-blocked, or removed)."
    if "sign in to confirm" in err or "not a bot" in err or "bot" in err:
        return (
            "YouTube is blocking this server's IP (bot check). "
            "Fix: Upload your cookies.txt file to backend/cookies/cookies.txt "
            "and set YOUTUBE_COOKIES_FILE=/app/cookies/cookies.txt in Render environment variables."
        )
    if "unable to extract" in err or "failed to extract" in err:
        return "YouTube changed something yt-dlp doesn't recognize yet. Run: pip install -U yt-dlp"
    if "certificate" in err or "ssl" in err:
        return "SSL/certificate error reaching YouTube."
    if "http error 429" in err or "too many requests" in err:
        return "YouTube is rate-limiting this server. Wait a few minutes and try again."
    if "no video formats found" in err or "requested format is not available" in err:
        return "No downloadable format found for this video."
    if "ffmpeg" in err and ("not found" in err or "is not installed" in err):
        return "yt-dlp could not find FFmpeg. Check FFMPEG_PATH in backend/.env."

    # Look for specific lines containing "ERROR:" or "error:"
    for line in (raw_output or "").splitlines():
        if "error:" in line.lower():
            return f"yt-dlp error: {line.strip()}"

    # Fall back to the end of the raw output if no explicit error line is found
    if raw_output:
        lines = raw_output.strip().splitlines()
        last_few = " ".join(lines[-3:]) if len(lines) >= 3 else raw_output.strip()
        cleaned = last_few.replace("\n", " ")[:400]
    else:
        cleaned = "Unknown error"
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

    clean_url = _clean_url(url)
    output_template = os.path.join(abs_dir, f"{video_id}.%(ext)s")
    final_mp4 = os.path.join(abs_dir, f"{video_id}.mp4")
    ffmpeg_dir = os.path.dirname(os.path.abspath(FFMPEG_BIN))
    format_selector = _build_format_selector()

    cookies = _cookies_args()
    if cookies:
        print(f"[youtube] Using cookies file: {COOKIES_FILE}")
    else:
        print("[youtube] WARNING: No cookies file found. YouTube may block this download.")

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
        "--no-check-certificate",
        *cookies,          # --cookies cookies.txt if available
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
            full_path = os.path.join(abs_dir, fname)
            if os.path.isfile(full_path):
                return full_path

    tail = "\n".join(full_output_lines[-15:]) if full_output_lines else "(no output)"
    raise RuntimeError(
        f"yt-dlp reported success but no output file found in {abs_dir}.\n"
        f"Last yt-dlp output:\n{tail}"
    )