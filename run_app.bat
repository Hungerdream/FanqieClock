@echo off
echo Starting Fanqie Clock Desktop...
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)
python src/main.py
pause