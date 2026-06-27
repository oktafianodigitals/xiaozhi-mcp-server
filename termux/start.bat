@echo off
REM start.bat — launcher untuk Windows.
REM Membuat virtual environment kalau belum ada, pasang dependency, lalu
REM jalankan server. Jalankan dengan double-click atau dari cmd/PowerShell.

cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python tidak ditemukan di PATH. Install dari https://python.org dan pastikan "Add to PATH" dicentang.
    pause
    exit /b 1
)

if not exist ".venv\" (
    echo [setup] Membuat virtual environment di .venv ...
    python -m venv .venv
)

call ".venv\Scripts\activate.bat"

if not exist ".venv\.deps_installed" (
    echo [setup] Memasang dependency dari requirements.txt ...
    python -m pip install --upgrade pip --quiet
    pip install -r requirements.txt --quiet
    echo done > ".venv\.deps_installed"
)

echo [run] Menjalankan xiaozhi-mcp-console ...
python main.py

pause
