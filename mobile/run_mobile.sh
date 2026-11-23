#!/bin/bash
cd "$(dirname "$0")"

# Запуск мобильного приложения Key Tracker на Flet
if [ -f "../.venv/bin/python" ]; then
    ../.venv/bin/python main.py
elif [ -f ".venv/bin/python" ]; then
    .venv/bin/python main.py
else
    python3 main.py
fi
