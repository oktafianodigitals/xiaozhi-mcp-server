"""
mcp/tools/_browser.py

Helper bersama untuk membuka URL di Brave browser pada mesin Windows tempat
server ini berjalan (lihat start.bat — server didesain jalan lokal di
komputer yang sama dengan browser, bukan di cloud).

Strategi pencarian brave.exe (urutan prioritas):
1. Path manual dari dashboard Settings (config: browser.brave_path), kalau diisi.
2. Lokasi instalasi umum Brave di Windows (Program Files, per-user AppData).
3. Command "brave" di PATH (kalau user sudah menambahkannya sendiri).

Kalau ketiganya gagal, ToolConfigError dilempar dengan pesan yang menuntun
user mengisi path manual di dashboard.
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
    """Cari path brave.exe yang valid. Urutan: config manual -> lokasi umum
    Windows -> PATH. Melempar ToolConfigError kalau semuanya gagal."""

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


def open_url_in_brave(url: str) -> str:
    """Buka URL di Brave lewat proses baru (non-blocking) dan kembalikan path
    executable yang dipakai. Melempar ToolConfigError kalau brave.exe tidak
    ditemukan, atau RuntimeError kalau proses gagal dijalankan."""

    brave_path = find_brave_executable()
    try:
        # Popen (bukan run/call) supaya tool ini tidak menunggu Brave ditutup —
        # cukup memicu proses lalu langsung kembali ke caller.
        subprocess.Popen([brave_path, url])
    except OSError as exc:
        raise RuntimeError(f"Gagal menjalankan Brave di '{brave_path}': {exc}") from exc

    logger.info("Membuka Brave (%s) dengan URL: %s", brave_path, url)
    return brave_path
