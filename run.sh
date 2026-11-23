#!/bin/bash
# Запуск Key Tracker V2
cd "$(dirname "$0")"
if /usr/bin/python3 -c "import customtkinter" 2>/dev/null; then
    /usr/bin/python3 app.py
else
    python3 app.py
fi
