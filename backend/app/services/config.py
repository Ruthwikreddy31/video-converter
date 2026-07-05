"""
Central config — resolves paths for ffmpeg, ffprobe, yt-dlp on Windows & Linux/Mac.

Priority order:
  1. Value set in .env  (e.g. FFMPEG_PATH=C:\\ffmpeg\\bin\\ffmpeg.exe)
  2. Common Windows install locations (C:\\ffmpeg\\bin\\, user home, etc.)
  3. System PATH  (works if you added C:\\ffmpeg\\bin to PATH)
"""
import os
import shutil
import sys
import subprocess


def _find_executable(name: str, env_key: str, windows_hints: list) -> str:
    # 1. Explicit path from .env
    from_env = os.getenv(env_key, "").strip().strip('"').strip("'")
    if from_env:
        if os.path.isfile(from_env):
            return from_env
        # The user set it but the file doesn't exist — warn but continue
        print(f"[config] WARNING: {env_key}={from_env!r} but file not found there.")

    # 2. Common Windows locations
    if sys.platform == "win32":
        for hint in windows_hints:
            if hint and os.path.isfile(hint):
                return hint

    # 3. System PATH
    found = shutil.which(name)
    if found:
        return found

    # 4. Nothing found — return bare name and let the OS give a clear error
    return name


_user_profile = os.environ.get("USERPROFILE", "")
_local_app    = os.environ.get("LOCALAPPDATA", "")
_app_data     = os.environ.get("APPDATA", "")

FFMPEG_BIN = _find_executable(
    name="ffmpeg",
    env_key="FFMPEG_PATH",
    windows_hints=[
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
        os.path.join(_user_profile, "ffmpeg", "bin", "ffmpeg.exe"),
        os.path.join(_local_app, "Programs", "ffmpeg", "bin", "ffmpeg.exe"),
    ]
)

FFPROBE_BIN = _find_executable(
    name="ffprobe",
    env_key="FFPROBE_PATH",
    windows_hints=[
        r"C:\ffmpeg\bin\ffprobe.exe",
        r"C:\Program Files\ffmpeg\bin\ffprobe.exe",
        r"C:\Program Files (x86)\ffmpeg\bin\ffprobe.exe",
        os.path.join(_user_profile, "ffmpeg", "bin", "ffprobe.exe"),
        os.path.join(_local_app, "Programs", "ffmpeg", "bin", "ffprobe.exe"),
    ]
)

YTDLP_BIN = _find_executable(
    name="yt-dlp",
    env_key="YTDLP_PATH",
    windows_hints=[
        # pip install puts it here
        os.path.join(sys.prefix, "Scripts", "yt-dlp.exe"),
        os.path.join(_app_data,  "Python", "Scripts", "yt-dlp.exe"),
        os.path.join(_local_app, "Programs", "Python", "Scripts", "yt-dlp.exe"),
        # Windows Store Python user-installed packages
        os.path.join(_local_app, "Packages", f"PythonSoftwareFoundation.Python.{sys.version_info.major}.{sys.version_info.minor}_qbz5n2kfra8p0", "LocalCache", "local-packages", f"Python{sys.version_info.major}{sys.version_info.minor}", "Scripts", "yt-dlp.exe"),
        # winget / scoop / manual
        r"C:\yt-dlp\yt-dlp.exe",
        os.path.join(_user_profile, "yt-dlp", "yt-dlp.exe"),
        os.path.join(_user_profile, "scoop", "shims", "yt-dlp.exe"),
    ]
)

# On Windows, prevent console windows from popping up on every subprocess call.
# NOTE: do NOT use CREATE_NO_WINDOW together with stdout=PIPE in Popen —
#       strip it in callers that need to read stdout (yt-dlp download).
SUBPROCESS_FLAGS: dict = {}
if sys.platform == "win32":
    SUBPROCESS_FLAGS["creationflags"] = subprocess.CREATE_NO_WINDOW

# Runtime dirs
UPLOAD_DIR  = os.getenv("UPLOAD_DIR",  "uploads")
OUTPUT_DIR  = os.getenv("OUTPUT_DIR",  "outputs")
PREVIEW_DIR = os.getenv("PREVIEW_DIR", "previews")

for _d in (UPLOAD_DIR, OUTPUT_DIR, PREVIEW_DIR):
    os.makedirs(_d, exist_ok=True)


# ── Startup check ──────────────────────────────────────────────────────────────
def check_dependencies() -> dict:
    """Check which tools are available. Call GET /api/status/deps to see results."""
    results = {}
    for name, path in [("ffmpeg", FFMPEG_BIN), ("ffprobe", FFPROBE_BIN), ("yt-dlp", YTDLP_BIN)]:
        try:
            flag = "--version" if name == "yt-dlp" else "-version"
            r = subprocess.run(
                [path, flag],
                capture_output=True, text=True, timeout=10,
                **SUBPROCESS_FLAGS
            )
            version_line = r.stdout.splitlines()[0] if r.stdout else "unknown"
            results[name] = {
                "ok": r.returncode == 0,
                "path": path,
                "version": version_line,
            }
        except FileNotFoundError:
            results[name] = {
                "ok": False,
                "path": path,
                "version": None,
                "error": (
                    f"'{path}' not found. "
                    f"Set {name.upper().replace('-','_')}_PATH in backend/.env "
                    f"or add it to your system PATH."
                ),
            }
        except Exception as e:
            results[name] = {"ok": False, "path": path, "version": None, "error": str(e)}
    return results


def print_startup_check():
    """Print dependency status to the uvicorn console on startup."""
    print("\n" + "="*55)
    print("  IMAX CONVERTER - Dependency Check")
    print("="*55)
    results = check_dependencies()
    all_ok = True
    for name, info in results.items():
        icon = "[OK]" if info["ok"] else "[ERR]"
        print(f"  {icon}  {name:<10} {info['path']}")
        if not info["ok"]:
            all_ok = False
            print(f"         ERROR: {info.get('error','')}")
    if not all_ok:
        print()
        print("  [!]  Fix: Open http://localhost:8000/api/status/deps")
        print("  [!]  Windows FFmpeg: https://www.gyan.dev/ffmpeg/builds/")
        print("  [!]  yt-dlp:  pip install yt-dlp")
        print()
        print("  Set paths in backend/.env:")
        print("    FFMPEG_PATH=C:\\ffmpeg\\bin\\ffmpeg.exe")
        print("    FFPROBE_PATH=C:\\ffmpeg\\bin\\ffprobe.exe")
    print("="*55 + "\n")
