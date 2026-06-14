#!/bin/bash
# ==============================================================================
# Setup Dev Environment - Cognitive Voice Intelligence Platform
# ==============================================================================

set -e

echo "🚀 Starting development environment setup..."

# 1. Check for system dependencies
echo "🔍 Checking for system dependencies..."

if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is not installed. Please install Python 3.10+."
    exit 1
fi

if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  Warning: ffmpeg is not found on your system PATH."
    echo "   Faster-Whisper and audio processing require FFmpeg to transcode files."
    echo "   macOS: 'brew install ffmpeg' | Linux: 'sudo apt install ffmpeg'"
fi

# 2. Setup environment files
echo "📝 Copying environment variable templates..."

# Root env
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ Created root .env file"
else
    echo "ℹ️  Root .env already exists. Skipping."
fi

# Backend env
if [ ! -f backend/.env ]; then
    cp backend/.env.example backend/.env
    echo "✅ Created backend/.env file"
else
    echo "ℹ️  backend/.env already exists. Skipping."
fi

# Frontend env
if [ ! -f frontend/.env.local ]; then
    cp frontend/.env.example frontend/.env.local
    echo "✅ Created frontend/.env.local file"
else
    echo "ℹ️  frontend/.env.local already exists. Skipping."
fi

# 3. Build Python virtual environment
echo "🐍 Setting up python virtual environment..."
cd backend

if [ ! -d venv ]; then
    python3 -m venv venv
    echo "✅ Python virtual environment created at backend/venv"
fi

# Activate virtualenv and install packages
source venv/bin/activate
echo "📦 Installing backend dependencies in virtualenv..."
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ Python libraries installed successfully!"

cd ..

echo "🎉 Developer environment initialized!"
echo "--------------------------------------------------------"
echo "To run the backend server:"
echo "  cd backend"
echo "  source venv/bin/activate"
echo "  uvicorn app.main:app --reload"
echo "--------------------------------------------------------"
echo "To run the frontend client:"
echo "  cd frontend"
echo "  npm install"
echo "  npm run dev"
echo "--------------------------------------------------------"
