#!/bin/bash
# Запуск мобильного приложения Key Tracker (Flet)
cd "$(dirname "$0")"

if /Library/Frameworks/Python.framework/Versions/3.15/bin/python3 -c "import flet" 2>/dev/null; then
    PYTHON_CMD="/Library/Frameworks/Python.framework/Versions/3.15/bin/python3"
elif /opt/homebrew/bin/python3.12 -c "import flet" 2>/dev/null; then
    PYTHON_CMD="/opt/homebrew/bin/python3.12"
else
    PYTHON_CMD="python3"
fi

echo "📱 Запуск мобильной версии (Flet) через $PYTHON_CMD..."
exec $PYTHON_CMD main.py
