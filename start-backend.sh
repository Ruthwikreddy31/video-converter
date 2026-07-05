#!/bin/bash
# Quick local dev startup script for the backend

echo "🎬 AI Video Aspect Ratio Converter — Backend"
echo "============================================"

cd "$(dirname "$0")/backend"

# Check FFmpeg
if ! command -v ffmpeg &>/dev/null; then
  echo "❌ FFmpeg not found. Install it:"
  echo "   macOS:   brew install ffmpeg"
  echo "   Ubuntu:  sudo apt install ffmpeg"
  exit 1
fi

echo "✅ FFmpeg: $(ffmpeg -version 2>&1 | head -1)"

# Check yt-dlp
if command -v yt-dlp &>/dev/null; then
  echo "✅ yt-dlp: $(yt-dlp --version)"
else
  echo "⚠️  yt-dlp not found — YouTube downloads won't work"
  echo "   Install: pip install yt-dlp"
fi

# Install deps
echo ""
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt -q

# Start server
echo ""
echo "🚀 Starting backend at http://localhost:8000"
echo "   API docs: http://localhost:8000/docs"
echo ""
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
