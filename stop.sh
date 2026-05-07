#!/bin/bash
cd "$(dirname "$0")"
PORT=${PORT:-8000}
PIDS=$(lsof -ti:$PORT 2>/dev/null)
if [ -n "$PIDS" ]; then
    echo "$PIDS" | xargs kill -9 2>/dev/null
    echo "✅ หยุดเซิร์ฟเวอร์ที่ port $PORT แล้ว"
else
    echo "ℹ️  ไม่มีเซิร์ฟเวอร์ทำงานอยู่ที่ port $PORT"
fi
