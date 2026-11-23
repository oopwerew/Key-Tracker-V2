#!/bin/bash
cd "$(dirname "$0")"

# Если есть виртуальное окружение в корне
if [ -f "../.venv/bin/python" ]; then
    ../.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
elif [ -f ".venv/bin/python" ]; then
    .venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
else
    python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
fi
