from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import uuid
import os

from app.services.youtube_service import validate_youtube_url, get_video_info, download_video
from app.services.ffmpeg_service import extract_video_info, generate_thumbnail
from app.services.preview_service import generate_all_previews

router = APIRouter()

# In-memory progress store
download_progress: dict = {}


class YouTubeRequest(BaseModel):
    url: str


@router.post("/info")
async def yt_info(request: YouTubeRequest):
    if not validate_youtube_url(request.url):
        raise HTTPException(400, "Invalid YouTube URL.")
    try:
        return get_video_info(request.url)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Could not fetch video info: {e}")


@router.post("/download")
async def yt_download(request: YouTubeRequest, background_tasks: BackgroundTasks):
    if not validate_youtube_url(request.url):
        raise HTTPException(400, "Invalid YouTube URL.")

    video_id = str(uuid.uuid4())
    download_progress[video_id] = {
        "status": "starting",
        "progress": 0,
        "message": "Initializing...",
    }
    background_tasks.add_task(_download_and_process, request.url, video_id)
    return {"video_id": video_id, "status": "downloading"}


def _download_and_process(url: str, video_id: str):
    try:
        # ── 1. Download ───────────────────────────────────────────────────────
        def cb(pct, msg):
            download_progress[video_id] = {
                "status": "downloading",
                "progress": pct,
                "message": msg,
            }

        download_progress[video_id] = {
            "status": "downloading", "progress": 0, "message": "Starting yt-dlp..."
        }

        file_path = download_video(url, "uploads", video_id, cb)

        abs_file = os.path.abspath(file_path)
        if not os.path.isfile(abs_file):
            raise RuntimeError(
                f"Downloaded file not found at: {abs_file}. "
                "Check FFMPEG_PATH in backend/.env — yt-dlp needs ffmpeg to merge video+audio."
            )

        # ── 2. Analyze ────────────────────────────────────────────────────────
        download_progress[video_id] = {
            "status": "analyzing", "progress": 100, "message": "Analyzing video..."
        }
        info = extract_video_info(abs_file)

        # ── 3. Thumbnail ──────────────────────────────────────────────────────
        download_progress[video_id]["message"] = "Generating thumbnail..."
        os.makedirs("previews", exist_ok=True)
        thumb_path = os.path.join("previews", f"{video_id}_thumb.jpg")
        generate_thumbnail(abs_file, thumb_path)

        # ── 4. Get title ──────────────────────────────────────────────────────
        try:
            title = get_video_info(url).get("title", "YouTube Video")
        except Exception:
            title = "YouTube Video"

        # ── 5. Save to DB (non-fatal) ─────────────────────────────────────────
        try:
            from app.database.database import SessionLocal, Video
            db = SessionLocal()
            try:
                db.add(Video(
                    id=video_id,
                    original_filename=f"{title}.mp4",
                    file_path=abs_file,
                    thumbnail_path=thumb_path,
                    width=info["width"], height=info["height"],
                    duration=info["duration"], fps=info["fps"],
                    file_size=info["file_size"],
                    aspect_ratio=info["aspect_ratio"],
                    detected_format=info["detected_format"],
                    video_codec=info["video_codec"],
                    audio_codec=info["audio_codec"],
                    source_type="youtube", youtube_url=url,
                ))
                db.commit()
            finally:
                db.close()
        except Exception as e:
            print(f"[youtube] DB save failed (non-fatal): {e}")

        # ── 6. Generate previews ──────────────────────────────────────────────
        download_progress[video_id]["message"] = "Generating format previews..."
        generate_all_previews(abs_file, video_id, info, "previews")

        # ── Done ──────────────────────────────────────────────────────────────
        download_progress[video_id] = {
            "status": "complete",
            "progress": 100,
            "message": "Ready",
            "video_id": video_id,
            "info": info,
            "thumbnail_url": f"/previews/{video_id}_thumb.jpg",
            "video_url": f"/uploads/{video_id}.mp4",
        }

    except Exception as e:
        print(f"[youtube] Download failed for video_id={video_id}: {e}")
        download_progress[video_id] = {
            "status": "error",
            "progress": 0,
            "message": str(e),
        }


@router.get("/progress/{video_id}")
async def yt_progress(video_id: str):
    p = download_progress.get(video_id)
    if not p:
        raise HTTPException(404, "No download found for this ID.")
    return p
