#!/bin/bash
# Quick local dev startup script for the frontend

echo "🎬 AI Video Aspect Ratio Converter — Frontend"
echo "==============================================="

cd "$(dirname "$0")/frontend"

echo "📦 Installing dependencies..."
npm install

echo ""
echo "🚀 Starting frontend at http://localhost:5173"
echo ""
npm run dev
