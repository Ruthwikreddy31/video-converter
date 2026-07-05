from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from app.routers import upload, youtube, convert, status
from app.database.database import engine, Base, test_db_connection
from app.services.config import print_startup_check

# Create tables
try:
    Base.metadata.create_all(bind=engine)
    print("[DB] Tables created/verified OK")
except Exception as e:
    print(f"[DB] WARNING: Could not create tables: {e}")
    print("[DB] App will still start — check your DATABASE_URL in .env")

# Print tool dependency check
print_startup_check()

# Print DB connection status
db_status = test_db_connection()
if db_status["ok"]:
    print(f"[DB] [OK] Connected to: {db_status['url']}")
else:
    print(f"[DB] [ERR] Connection failed: {db_status['error']}")
    print("[DB] Fix DATABASE_URL in backend/.env")
    print("[DB] For local dev use: DATABASE_URL=sqlite:///./video_converter.db")

app = FastAPI(
    title="AI Video Aspect Ratio Converter",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:3000,http://localhost:5174"
    ).split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("uploads",  exist_ok=True)
os.makedirs("outputs",  exist_ok=True)
os.makedirs("previews", exist_ok=True)

app.mount("/uploads",  StaticFiles(directory="uploads"),  name="uploads")
app.mount("/outputs",  StaticFiles(directory="outputs"),  name="outputs")
app.mount("/previews", StaticFiles(directory="previews"), name="previews")

app.include_router(upload.router,  prefix="/api/upload",  tags=["Upload"])
app.include_router(youtube.router, prefix="/api/youtube", tags=["YouTube"])
app.include_router(convert.router, prefix="/api/convert", tags=["Convert"])
app.include_router(status.router,  prefix="/api/status",  tags=["Status"])


@app.get("/")
async def root():
    return {"message": "AI Video Aspect Ratio Converter API", "version": "1.0.0"}

@app.get("/health")
async def health():
    db = test_db_connection()
    return {"status": "healthy", "database": db}
