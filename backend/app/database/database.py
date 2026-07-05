from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./video_converter.db")

# ── Engine setup ──────────────────────────────────────────────────────────────
# Handle both SQLite (local dev) and PostgreSQL (NeonDB / production)
if "sqlite" in DATABASE_URL:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    # PostgreSQL / NeonDB
    # NeonDB serverless requires connect_timeout and keepalives
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,          # test connection before using from pool
        pool_recycle=300,            # recycle connections every 5 min
        pool_size=5,
        max_overflow=10,
        connect_args={
            "connect_timeout": 10,
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
            "sslmode": "require",    # NeonDB always requires SSL
        },
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ── Models ────────────────────────────────────────────────────────────────────
class Video(Base):
    __tablename__ = "videos"

    id               = Column(String, primary_key=True)
    original_filename = Column(String, nullable=False)
    file_path        = Column(String, nullable=False)
    thumbnail_path   = Column(String, nullable=True)
    width            = Column(Integer, nullable=True)
    height           = Column(Integer, nullable=True)
    duration         = Column(Float,   nullable=True)
    fps              = Column(Float,   nullable=True)
    file_size        = Column(Integer, nullable=True)
    aspect_ratio     = Column(String,  nullable=True)
    detected_format  = Column(String,  nullable=True)
    video_codec      = Column(String,  nullable=True)
    audio_codec      = Column(String,  nullable=True)
    source_type      = Column(String,  default="upload")
    youtube_url      = Column(String,  nullable=True)
    created_at       = Column(DateTime, default=datetime.utcnow)


class Conversion(Base):
    __tablename__ = "conversions"

    id              = Column(String, primary_key=True)
    video_id        = Column(String, nullable=False)
    target_format   = Column(String, nullable=False)
    status          = Column(String, default="pending")
    output_path     = Column(String, nullable=True)
    preview_path    = Column(String, nullable=True)
    processing_time = Column(Float,  nullable=True)
    error_message   = Column(Text,   nullable=True)
    crop_method     = Column(String, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)
    completed_at    = Column(DateTime, nullable=True)
    progress        = Column(Integer, default=0)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_db_connection() -> dict:
    """Test the database connection and return status."""
    try:
        with engine.connect() as conn:
            from sqlalchemy import text
            conn.execute(text("SELECT 1"))
        return {"ok": True, "url": DATABASE_URL[:40] + "..."}
    except Exception as e:
        return {"ok": False, "error": str(e), "url": DATABASE_URL[:40] + "..."}
