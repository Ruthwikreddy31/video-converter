from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime
import uuid, os, time, threading

from app.database.database import get_db, Video, Conversion
from app.services.ffmpeg_service import convert_video, extract_video_info
from app.services.smart_crop import get_smart_crop_or_center

router = APIRouter()
conversion_progress: dict = {}

# Hard ceiling for the "detecting subjects" step. If smart-crop detection
# doesn't finish within this window for any reason, we stop waiting on it
# and proceed with a plain center crop instead of hanging forever.
SMART_CROP_WATCHDOG_SECONDS = 6


class ConversionRequest(BaseModel):
    video_id: str
    target_format: str   # scope | digital_imax | full_imax
    crop_method: str = "smart"


@router.post("/start")
async def start_conversion(
    request: ConversionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    allowed_formats = ["scope", "digital_imax", "full_imax", "imax_70mm", "imax_digital", "70mm_std", "35mm_std", "large_format", "dolby_vision"]
    clean_format = request.target_format.replace("_border", "")
    if clean_format not in allowed_formats:
        raise HTTPException(400, f"Invalid format. Choose one of: {', '.join(allowed_formats)}")

    # Find the video file — try DB first, then filesystem scan
    video_path = None
    try:
        video = db.query(Video).filter(Video.id == request.video_id).first()
        if video and os.path.isfile(video.file_path):
            video_path = video.file_path
    except Exception as e:
        print(f"[convert] DB query failed: {e}")

    # Fallback: scan uploads directory
    if not video_path:
        for ext in [".mp4", ".mov", ".mkv", ".avi", ".webm"]:
            candidate = os.path.join("uploads", f"{request.video_id}{ext}")
            if os.path.isfile(candidate):
                video_path = os.path.abspath(candidate)
                break

    if not video_path:
        raise HTTPException(404, f"Video file not found for id: {request.video_id}")

    cid = str(uuid.uuid4())

    # Save conversion to DB (non-fatal)
    try:
        db.add(Conversion(
            id=cid, video_id=request.video_id,
            target_format=request.target_format,
            status="pending", crop_method=request.crop_method,
        ))
        db.commit()
    except Exception as e:
        print(f"[convert] DB save failed (non-fatal): {e}")

    conversion_progress[cid] = {"status": "pending", "progress": 0, "message": "Queued..."}

    background_tasks.add_task(
        _run_conversion, cid, video_path, request.target_format, request.crop_method
    )
    return {"conversion_id": cid, "status": "pending"}


def _run_conversion(cid, video_path, target_format, crop_method):
    t0 = time.time()
    try:
        conversion_progress[cid] = {"status": "processing", "progress": 5, "message": "Analyzing video..."}

        info = extract_video_info(video_path)
        conversion_progress[cid]["progress"] = 15

        # Smart crop detection — guarded so it can NEVER hang the conversion.
        # A watchdog timer fires after SMART_CROP_WATCHDOG_SECONDS regardless
        # of what get_smart_crop_or_center() is doing internally; if the main
        # call hasn't returned by then, we proceed with center crop anyway.
        smart = None
        actual_method = crop_method

        if crop_method == "smart":
            conversion_progress[cid]["message"] = "Detecting subjects..."

            detection_result = {"value": None, "done": False}

            def _run_detection():
                try:
                    detection_result["value"] = get_smart_crop_or_center(
                        video_path, info["width"], info["height"]
                    )
                except Exception as e:
                    print(f"[convert] Smart crop raised an exception: {e}")
                finally:
                    detection_result["done"] = True

            detection_thread = threading.Thread(target=_run_detection, daemon=True)
            detection_thread.start()
            detection_thread.join(timeout=SMART_CROP_WATCHDOG_SECONDS)

            if detection_result["done"] and detection_result["value"]:
                smart = detection_result["value"]
                actual_method = smart.get("method", "center")
                print(f"[convert] Smart crop result: {smart}")
            else:
                # Either it raised, timed out, or returned nothing useful —
                # proceed with plain center crop instead of waiting forever.
                print("[convert] Smart crop did not complete in time — using center crop")
                smart = None
                actual_method = "center"

            conversion_progress[cid]["progress"] = 18
            conversion_progress[cid]["message"] = f"Crop method: {actual_method}"

        os.makedirs("outputs", exist_ok=True)
        out_path = os.path.abspath(os.path.join("outputs", f"{cid}_{target_format}.mp4"))

        def cb(pct):
            conversion_progress[cid] = {
                "status": "processing",
                "progress": 20 + int(pct * 0.75),
                "message": f"Converting... {pct}%",
            }

        result = convert_video(
            video_path, out_path, target_format, info,
            actual_method, smart, cb
        )

        if not result.get("success"):
            conversion_progress[cid] = {
                "status": "needs_expansion",
                "progress": 0,
                "message": result.get("message"),
                "needs_ai_expansion": True,
            }
            _update_db(cid, "needs_expansion", error_message=result.get("message"))
            return

        elapsed = round(time.time() - t0, 1)
        conversion_progress[cid] = {
            "status": "completed",
            "progress": 100,
            "message": "Done!",
            "output_url": f"/outputs/{cid}_{target_format}.mp4",
            "processing_time": elapsed,
            "crop_method": actual_method,
        }
        _update_db(cid, "completed", out_path, elapsed, actual_method)

    except Exception as e:
        conversion_progress[cid] = {
            "status": "failed", "progress": 0, "message": str(e)
        }
        _update_db(cid, "failed", error_message=str(e))


def _update_db(cid, status, output_path=None, processing_time=None,
               crop_method=None, error_message=None):
    try:
        from app.database.database import SessionLocal
        db = SessionLocal()
        try:
            conv = db.query(Conversion).filter(Conversion.id == cid).first()
            if conv:
                conv.status = status
                if output_path:      conv.output_path = output_path
                if processing_time:  conv.processing_time = processing_time
                if crop_method:      conv.crop_method = crop_method
                if error_message:    conv.error_message = error_message
                if status in ("completed", "failed", "needs_expansion"):
                    conv.completed_at = datetime.utcnow()
                db.commit()
        finally:
            db.close()
    except Exception as e:
        print(f"[convert] DB update failed (non-fatal): {e}")


@router.get("/progress/{conversion_id}")
async def get_progress(conversion_id: str):
    p = conversion_progress.get(conversion_id)
    if not p:
        raise HTTPException(404, "Conversion not found.")
    return p


@router.get("/history")
async def get_history(db: Session = Depends(get_db)):
    try:
        convs = db.query(Conversion).order_by(Conversion.created_at.desc()).limit(50).all()
        out = []
        for c in convs:
            v = None
            try:
                v = db.query(Video).filter(Video.id == c.video_id).first()
            except Exception:
                pass
            out.append({
                "id": c.id, "video_id": c.video_id,
                "filename": v.original_filename if v else "Unknown",
                "target_format": c.target_format, "status": c.status,
                "crop_method": c.crop_method,
                "processing_time": c.processing_time,
                "output_url": f"/{c.output_path}" if c.output_path else None,
                "thumbnail_url": f"/{v.thumbnail_path}" if v and v.thumbnail_path else None,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "completed_at": c.completed_at.isoformat() if c.completed_at else None,
            })
        return out
    except Exception as e:
        print(f"[history] DB error: {e}")
        return []
