@echo off
cd /d %~dp0

if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
)
call .venv\Scripts\activate.bat

pip install -r requirements.txt || ( echo [ERROR] pip install failed & exit /b 1 )
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
