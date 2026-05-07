#!/bin/bash
cd "$(dirname "$0")"

# Stop any existing server on port 8000
PORT=${PORT:-8000}
PIDS=$(lsof -ti:$PORT 2>/dev/null)
if [ -n "$PIDS" ]; then
    echo "⛔ หยุดเซิร์ฟเวอร์เก่าที่ port $PORT..."
    echo "$PIDS" | xargs kill -9 2>/dev/null
    sleep 1
fi

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r backend/requirements.txt
else
    source venv/bin/activate
fi

echo "🚀 Starting War Alert Bot on http://localhost:$PORT"
cd backend && python3 main.py
