from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database.database import get_db, Video, Conversion
from app.services.config import check_dependencies, FFMPEG_BIN, FFPROBE_BIN, YTDLP_BIN

router = APIRouter()

@router.get("/deps")
async def check_deps():
    """Open http://localhost:8000/api/status/deps to diagnose WinError 2"""
    results = check_dependencies()
    return {"all_ok": all(v["ok"] for v in results.values()), "tools": results,
            "resolved_paths": {"ffmpeg":FFMPEG_BIN,"ffprobe":FFPROBE_BIN,"yt-dlp":YTDLP_BIN}}

@router.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    total_v = db.query(Video).count()
    total_c = db.query(Conversion).count()
    done    = db.query(Conversion).filter(Conversion.status=="completed").count()
    failed  = db.query(Conversion).filter(Conversion.status=="failed").count()
    fmt_counts = {r[0]:r[1] for r in db.query(Conversion.target_format,
                  func.count(Conversion.id)).group_by(Conversion.target_format).all()}
    avg = db.query(func.avg(Conversion.processing_time)).filter(
          Conversion.processing_time.isnot(None)).scalar()
    return {"total_videos":total_v,"total_conversions":total_c,
            "completed_conversions":done,"failed_conversions":failed,
            "success_rate":round(done/total_c*100,1) if total_c else 0,
            "format_breakdown":fmt_counts,
            "most_used_format":max(fmt_counts,key=fmt_counts.get) if fmt_counts else "N/A",
            "avg_processing_time_seconds":round(float(avg),1) if avg else 0}