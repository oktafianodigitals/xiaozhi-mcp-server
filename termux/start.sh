#!/usr/bin/env bash
# start.sh — launcher untuk Linux, macOS, dan Termux (Android).
# Membuat virtualenv kalau belum ada, pasang dependency, lalu jalankan server.
set -e

cd "$(dirname "$0")"

# Pilih interpreter Python yang tersedia (Termux kadang hanya punya `python`,
# bukan `python3`).
if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "Python tidak ditemukan. Di Termux: pkg install python" >&2
    exit 1
fi

VENV_DIR=".venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "[setup] Membuat virtual environment di $VENV_DIR ..."
    "$PY" -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

if [ ! -f "$VENV_DIR/.deps_installed" ] || [ "requirements.txt" -nt "$VENV_DIR/.deps_installed" ]; then
    echo "[setup] Memasang dependency dari requirements.txt ..."
    pip install --upgrade pip --quiet
    pip install -r requirements.txt --quiet
    touch "$VENV_DIR/.deps_installed"
fi

# Catatan Termux: kalau ingin server tetap jalan saat layar HP terkunci,
# jalankan `termux-wake-lock` di sesi terpisah sebelum start.sh ini, dan
# pertimbangkan memakai `tmux`/`screen` supaya proses tidak ikut mati saat
# sesi Termux ditutup.
echo "[run] Menjalankan xiaozhi-mcp-console ..."
exec "$PY" main.py
