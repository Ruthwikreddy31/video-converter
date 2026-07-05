# Triggering reload
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from dotenv import load_dotenv

load_dotenv()

from app.routers import upload, youtube, convert, status
from app.database.database import engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Video Aspect Ratio Converter",
    description="Convert videos to IMAX, Digital IMAX, and Scope formats",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("uploads", exist_ok=True)
os.makedirs("outputs", exist_ok=True)
os.makedirs("previews", exist_ok=True)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")
app.mount("/previews", StaticFiles(directory="previews"), name="previews")

app.include_router(upload.router, prefix="/api/upload", tags=["Upload"])
app.include_router(youtube.router, prefix="/api/youtube", tags=["YouTube"])
app.include_router(convert.router, prefix="/api/convert", tags=["Convert"])
app.include_router(status.router, prefix="/api/status", tags=["Status"])


@app.get("/")
async def root():
    return {"message": "AI Video Aspect Ratio Converter API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
