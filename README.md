# 🎬 AI Video Aspect Ratio Converter

Convert any video to cinema formats: **Scope (2.39:1)**, **Digital IMAX (1.90:1)**, and **Full IMAX (1.43:1)** using AI-powered smart cropping and FFmpeg.

---

## Features

- **YouTube URL support** — paste any YouTube link and download at highest quality
- **Local video upload** — MP4, MOV, MKV, AVI, WEBM up to 2GB
- **Auto-detection** — FFprobe analyzes resolution, aspect ratio, FPS, codec, duration
- **Format detection** — auto-detects Scope, Digital IMAX, Full IMAX, 16:9, and more
- **Smart Crop** — OpenCV face/person detection keeps subjects centered
- **Preview grid** — side-by-side comparison of all 4 formats before conversion
- **Full IMAX expansion warning** — detects when source lacks vertical image data
- **Conversion history** — track all jobs with status and download links
- **Admin dashboard** — format breakdown, processing stats, success rates

---

## Tech Stack

| Layer | Tech |
|---|---|
| Frontend | React 18, TypeScript, TailwindCSS, Vite |
| Backend | FastAPI, Python 3.11 |
| Video | FFmpeg, FFprobe |
| AI Crop | OpenCV (Haar cascades + HOG) |
| YouTube | yt-dlp |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Container | Docker, Docker Compose |

---

## Quick Start (Docker)

```bash
# Clone and start
git clone <repo>
cd ai-video-converter
docker-compose up --build

# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
# API docs: http://localhost:8000/docs
```

---

## Local Development

### Backend

```bash
cd backend

# Install system deps (macOS)
brew install ffmpeg

# Install Python deps
pip install -r requirements.txt

# Run
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

---

## API Endpoints

### Upload
| Method | Path | Description |
|---|---|---|
| `POST` | `/api/upload/` | Upload local video file |
| `GET` | `/api/upload/{id}/info` | Get video info + preview URLs |

### YouTube
| Method | Path | Description |
|---|---|---|
| `POST` | `/api/youtube/info` | Get YouTube video metadata |
| `POST` | `/api/youtube/download` | Start async download |
| `GET` | `/api/youtube/progress/{id}` | Poll download progress |

### Convert
| Method | Path | Description |
|---|---|---|
| `POST` | `/api/convert/start` | Start conversion job |
| `GET` | `/api/convert/progress/{id}` | Poll conversion progress |
| `GET` | `/api/convert/history` | Get conversion history |

### Status
| Method | Path | Description |
|---|---|---|
| `GET` | `/api/status/stats` | Get processing statistics |

---

## Conversion Logic

### Scope (2.39:1)
- Wider than source → crop sides
- Taller than source → crop top/bottom
- Smart crop centers on detected faces/persons

### Digital IMAX (1.90:1)
- Same crop logic, different target ratio
- Best for 16:9 source videos

### Full IMAX (1.43:1)
- If source ratio < 2.0: direct crop/scale
- If source ratio > 2.0: warns that vertical data is missing
  - **Safe conversion**: letterbox padding
  - **AI Enhanced**: outpainting (planned)

---

## Smart Crop Pipeline

```
Video frame sample
↓
Try: Haar cascade face detection (OpenCV)
↓ (if none found)
Try: HOG person detector
↓ (if none found)
Fallback: rule-of-thirds center (width/2, height*0.45)
```

---

## Project Structure

```
ai-video-converter/
├── frontend/
│   ├── src/
│   │   ├── api/videoApi.ts          # All API calls
│   │   ├── components/
│   │   │   ├── Layout.tsx           # Nav + film strip wrapper
│   │   │   ├── UploadVideo.tsx      # Upload/YouTube tabs
│   │   │   ├── VideoInfo.tsx        # Metadata display
│   │   │   ├── ConversionOptions.tsx # Format selection + progress
│   │   │   └── PreviewGrid.tsx      # Side-by-side previews
│   │   └── pages/
│   │       ├── Home.tsx             # Main conversion flow
│   │       ├── Dashboard.tsx        # Stats
│   │       └── History.tsx          # Conversion log
│   └── ...
│
└── backend/
    ├── app/
    │   ├── main.py                  # FastAPI app + CORS
    │   ├── routers/
    │   │   ├── upload.py            # File upload endpoint
    │   │   ├── youtube.py           # YouTube download
    │   │   ├── convert.py           # Conversion jobs
    │   │   └── status.py            # Stats API
    │   ├── services/
    │   │   ├── ffmpeg_service.py    # FFprobe analysis + FFmpeg conversion
    │   │   ├── youtube_service.py   # yt-dlp wrapper
    │   │   ├── preview_service.py   # Preview frame generation
    │   │   └── smart_crop.py        # OpenCV subject detection
    │   └── database/
    │       └── database.py          # SQLAlchemy models + session
    └── requirements.txt
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./video_converter.db` | Database connection string |

---

## Production Notes

- For PostgreSQL: set `DATABASE_URL=postgresql://user:pass@host/db`
- For large files: increase nginx `client_max_body_size` and uvicorn timeout
- For Celery/Redis queue: replace `BackgroundTasks` with Celery workers
- For S3 storage: add boto3 and upload output files after conversion
