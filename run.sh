#!/bin/bash
# Запуск Key Tracker V2 (Fullstack Web & API Server)
cd "$(dirname "$0")"

# Выбираем доступный Python с поддержкой FastAPI
if /Library/Frameworks/Python.framework/Versions/3.15/bin/python3 -c "import fastapi" 2>/dev/null; then
    PYTHON_CMD="/Library/Frameworks/Python.framework/Versions/3.15/bin/python3"
elif /opt/homebrew/bin/python3.12 -c "import fastapi" 2>/dev/null; then
    PYTHON_CMD="/opt/homebrew/bin/python3.12"
else
    PYTHON_CMD="python3"
fi

echo "🚀 Запуск Key Tracker V2 через $PYTHON_CMD..."
open "http://localhost:8000" 2>/dev/null &
exec $PYTHON_CMD server.py
