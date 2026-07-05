from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from sqlalchemy.orm import Session
import uuid
import os

from app.database.database import get_db, Video
from app.services.ffmpeg_service import extract_video_info, generate_thumbnail
from app.services.preview_service import generate_all_previews

router = APIRouter()

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm"}
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2 GB


@router.post("/")
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    # ── Validate extension ────────────────────────────────────────────────────
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")

    video_id = str(uuid.uuid4())
    upload_path = os.path.abspath(os.path.join("uploads", f"{video_id}{ext}"))

    # ── Save file ─────────────────────────────────────────────────────────────
    try:
        os.makedirs("uploads", exist_ok=True)
        with open(upload_path, "wb") as f:
            total = 0
            while True:
                chunk = await file.read(1024 * 1024)  # 1 MB chunks
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_FILE_SIZE:
                    f.close()
                    os.remove(upload_path)
                    raise HTTPException(413, "File too large. Maximum size is 2 GB.")
                f.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        if os.path.exists(upload_path):
            os.remove(upload_path)
        raise HTTPException(500, f"File save failed: {e}")

    # ── Analyze with ffprobe ──────────────────────────────────────────────────
    try:
        info = extract_video_info(upload_path)
    except Exception as e:
        os.remove(upload_path)
        raise HTTPException(422, f"Could not analyze video: {e}")

    # ── Generate thumbnail ────────────────────────────────────────────────────
    os.makedirs("previews", exist_ok=True)
    thumb_path = os.path.join("previews", f"{video_id}_thumb.jpg")
    generate_thumbnail(upload_path, thumb_path)

    # ── Save to DB (non-fatal if DB is down) ──────────────────────────────────
    try:
        db.add(Video(
            id=video_id,
            original_filename=file.filename,
            file_path=upload_path,
            thumbnail_path=thumb_path,
            width=info["width"],
            height=info["height"],
            duration=info["duration"],
            fps=info["fps"],
            file_size=info["file_size"],
            aspect_ratio=info["aspect_ratio"],
            detected_format=info["detected_format"],
            video_codec=info["video_codec"],
            audio_codec=info["audio_codec"],
            source_type="upload",
        ))
        db.commit()
    except Exception as e:
        print(f"[upload] DB save failed (non-fatal): {e}")
        # Don't crash — still return success so user can convert

    # ── Generate previews in background ──────────────────────────────────────
    background_tasks.add_task(
        generate_all_previews, upload_path, video_id, info, "previews"
    )

    return {
        "video_id": video_id,
        "filename": file.filename,
        "thumbnail_url": f"/previews/{video_id}_thumb.jpg",
        "video_url": f"/uploads/{video_id}{ext}",
        "info": info,
    }


@router.get("/{video_id}/info")
async def get_video_info(video_id: str, db: Session = Depends(get_db)):
    """Get video info + available preview URLs."""
    # First try DB
    video = None
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
    except Exception as e:
        print(f"[upload] DB query failed: {e}")

    # Build previews from filesystem (works even if DB is down)
    previews = {}
    for key in ["original", "scope", "digital_imax", "full_imax"]:
        path = os.path.join("previews", f"{video_id}_{key}.jpg")
        if os.path.exists(path):
            previews[key] = f"/previews/{video_id}_{key}.jpg"

    if video:
        _, ext = os.path.splitext(video.file_path)
        return {
            "video_id": video.id,
            "filename": video.original_filename,
            "thumbnail_url": f"/{video.thumbnail_path}" if video.thumbnail_path else None,
            "video_url": f"/uploads/{video.id}{ext}",
            "previews": previews,
            "info": {
                "width": video.width,
                "height": video.height,
                "duration": video.duration,
                "fps": video.fps,
                "file_size": video.file_size,
                "aspect_ratio": video.aspect_ratio,
                "detected_format": video.detected_format,
                "video_codec": video.video_codec,
                "audio_codec": video.audio_codec,
            },
        }

    # Fallback: re-probe the file from disk if DB failed
    for ext in [".mp4", ".mov", ".mkv", ".avi", ".webm"]:
        file_path = os.path.join("uploads", f"{video_id}{ext}")
        if os.path.exists(file_path):
            try:
                info = extract_video_info(file_path)
                thumb = f"/previews/{video_id}_thumb.jpg"
                return {
                    "video_id": video_id,
                    "filename": f"video{ext}",
                    "video_url": f"/uploads/{video_id}{ext}",
                    "thumbnail_url": thumb if os.path.exists(thumb.lstrip("/")) else None,
                    "previews": previews,
                    "info": info,
                }
            except Exception:
                pass

    raise HTTPException(404, "Video not found")
