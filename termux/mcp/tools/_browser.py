"""
mcp/tools/_browser.py

Helper bersama untuk membuka URL video (YouTube) di browser pada mesin
tempat server ini berjalan. Server didesain jalan LOKAL di perangkat yang
sama dengan browser (lihat start.bat / start.sh) — bukan di cloud terpisah
— jadi "buka browser" di sini berarti browser di perangkat itu sendiri.

Dua platform yang didukung, dideteksi otomatis saat runtime:

1. WINDOWS — spawn proses brave.exe langsung lewat subprocess.Popen.
   Urutan pencarian brave.exe: config manual (browser.brave_path) ->
   lokasi instalasi umum (Program Files / AppData) -> command "brave" di PATH.

2. TERMUX (Android) — TIDAK ADA "brave.exe" untuk dieksekusi; Brave di Android
   adalah APK, bukan binary command-line. Sebagai gantinya, URL dibuka lewat
   Android Intent (ACTION_VIEW) menggunakan command `termux-open-url` dari
   paket Termux:API. Browser yang terbuka adalah BROWSER DEFAULT sistem
   Android (apa pun yang diset di Android Settings > Apps > Default apps),
   bukan Brave secara spesifik — Android tidak punya cara untuk memaksa
   Intent ke app tertentu tanpa tahu nama package & activity persis, dan itu
   di luar scope termux-open-url. Kalau Brave ingin selalu terbuka, set Brave
   sebagai browser default di Android.

   Prasyarat di Termux:
   - `pkg install termux-api`
   - Install app pendamping "Termux:API" dari F-Droid/Play Store
   Tanpa app pendamping ini, command `termux-open-url` akan gagal/timeout.

Platform lain (Linux desktop, macOS) tidak secara eksplisit didukung
deployment-nya, tapi fallback "brave di PATH" tetap dicoba sebagai best-effort.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pathlib import Path

from core.config import config
from core.logger import get_logger
from mcp.tools._http import ToolConfigError

logger = get_logger("mcp.tools.browser")

# Lokasi instalasi default Brave di Windows. %PROGRAMFILES% dan %LOCALAPPDATA%
# diresolve saat runtime karena bisa beda di tiap mesin (terutama drive
# instalasi & username).
_WINDOWS_CANDIDATE_TEMPLATES = [
    r"{programfiles}\BraveSoftware\Brave-Browser\Application\brave.exe",
    r"{programfiles_x86}\BraveSoftware\Brave-Browser\Application\brave.exe",
    r"{localappdata}\BraveSoftware\Brave-Browser\Application\brave.exe",
]


def is_termux() -> bool:
    """Deteksi sesi Termux. TERMUX_VERSION selalu di-set oleh Termux di setiap
    sesi shell, jadi ini sinyal paling reliable (lebih reliable daripada
    menebak dari sys.platform, yang tetap melaporkan 'linux' di Termux)."""
    return "TERMUX_VERSION" in os.environ


def _windows_candidates() -> list[str]:
    env = {
        "programfiles": os.environ.get("PROGRAMFILES", r"C:\Program Files"),
        "programfiles_x86": os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
        "localappdata": os.environ.get("LOCALAPPDATA", ""),
    }
    return [tmpl.format(**env) for tmpl in _WINDOWS_CANDIDATE_TEMPLATES]


def _configured_path() -> str:
    return (config.get("browser", "brave_path", default="") or "").strip()


def find_brave_executable() -> str:
    """Cari path brave.exe yang valid (khusus jalur Windows/desktop). Urutan:
    config manual -> lokasi umum Windows -> PATH. Melempar ToolConfigError
    kalau semuanya gagal. Tidak dipakai sama sekali di jalur Termux."""

    # 1) Path manual dari dashboard — paling diutamakan karena user yang tahu
    #    persis lokasi instalasinya kalau auto-detect tidak cocok.
    manual_path = _configured_path()
    if manual_path:
        if Path(manual_path).is_file():
            return manual_path
        logger.warning(
            "browser.brave_path di config ('%s') tidak ditemukan, lanjut auto-detect", manual_path
        )

    # 2) Lokasi instalasi umum (khusus Windows, sesuai target deployment server ini).
    if platform.system() == "Windows":
        for candidate in _windows_candidates():
            if candidate and Path(candidate).is_file():
                return candidate

    # 3) Fallback: "brave" di PATH (macOS/Linux pakai nama command, atau user
    #    Windows yang sudah menambahkan sendiri ke PATH).
    found = shutil.which("brave") or shutil.which("brave-browser")
    if found:
        return found

    raise ToolConfigError(
        "brave.exe tidak ditemukan secara otomatis. Buka dashboard > Settings > "
        "Browser, isi path lengkap ke brave.exe secara manual, lalu simpan."
    )


def _open_via_termux(url: str) -> str:
    """Buka URL lewat Android Intent (ACTION_VIEW) pakai termux-open-url dari
    paket Termux:API. Browser yang terbuka = browser default Android, bukan
    Brave secara spesifik (lihat docstring modul)."""

    termux_open_url = shutil.which("termux-open-url")
    if not termux_open_url:
        raise ToolConfigError(
            "Command 'termux-open-url' tidak ditemukan. Jalankan "
            "'pkg install termux-api' di Termux DAN install app pendamping "
            "'Termux:API' dari F-Droid/Play Store — keduanya wajib ada."
        )

    try:
        # run (bukan Popen) — termux-open-url cuma memicu Intent dan keluar
        # cepat (<1s), bukan proses jangka panjang seperti browser desktop.
        # timeout sebagai pengaman kalau Termux:API tidak merespons (app
        # pendamping belum di-grant izin / belum diinstall).
        result = subprocess.run(
            [termux_open_url, url], capture_output=True, text=True, timeout=10
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            "termux-open-url tidak merespons (timeout). Pastikan app "
            "'Termux:API' terinstall dan diberi izin yang diperlukan."
        ) from exc
    except OSError as exc:
        raise RuntimeError(f"Gagal menjalankan termux-open-url: {exc}") from exc

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        raise RuntimeError(
            f"termux-open-url gagal (exit {result.returncode})"
            + (f": {stderr}" if stderr else "")
        )

    logger.info("Membuka URL lewat termux-open-url (browser default Android): %s", url)
    return "termux-open-url"


def open_url_in_browser(url: str) -> str:
    """Titik masuk tunggal dipakai tool youtube.play_music / play_video.
    Mendeteksi platform lalu memilih strategi yang sesuai:
    - Termux  -> Android Intent lewat termux-open-url (browser default)
    - lainnya -> spawn brave.exe langsung (Windows/desktop)

    Mengembalikan string identitas browser/strategi yang dipakai, untuk
    ditampilkan di hasil tool. Melempar ToolConfigError / RuntimeError sesuai
    kegagalan masing-masing strategi.
    """
    if is_termux():
        return _open_via_termux(url)

    brave_path = find_brave_executable()
    try:
        # Popen (bukan run/call) supaya tool ini tidak menunggu Brave ditutup —
        # cukup memicu proses lalu langsung kembali ke caller.
        subprocess.Popen([brave_path, url])
    except OSError as exc:
        raise RuntimeError(f"Gagal menjalankan Brave di '{brave_path}': {exc}") from exc

    logger.info("Membuka Brave (%s) dengan URL: %s", brave_path, url)
    return brave_path
