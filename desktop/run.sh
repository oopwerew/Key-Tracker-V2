#!/bin/bash
# Запуск Key Tracker V2 (Desktop)
cd "$(dirname "$0")"

if [ -f "../.venv/bin/python" ]; then
    ../.venv/bin/python app.py
elif /usr/bin/python3 -c "import customtkinter" 2>/dev/null; then
    /usr/bin/python3 app.py
else
    python3 app.py
fi
