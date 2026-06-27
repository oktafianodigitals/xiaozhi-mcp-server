"""
mcp/tools/_http.py

Helper httpx untuk semua modul tool.

Default User-Agent sengaja deskriptif (bukan "python-httpx") karena
beberapa provider (Wikimedia, Frankfurter) memblokir client tanpa
identifikasi aplikasi yang jelas.
"""

from __future__ import annotations

import httpx

DEFAULT_TIMEOUT = httpx.Timeout(12.0, connect=6.0)

# User-Agent default untuk semua tool.
# Tool tertentu (wiki.py) meng-override ini dengan header yang lebih spesifik
# sesuai kebijakan Wikimedia API.
DEFAULT_HEADERS = {
    "User-Agent": "xiaozhi-mcp-console/1.1 (mcp-tool-bridge)",
    "Accept": "application/json",
}


def client(**kwargs) -> httpx.AsyncClient:
    """Buat httpx.AsyncClient dengan timeout dan header default.

    Kalau caller meneruskan `headers`, header itu akan MERGE dengan
    DEFAULT_HEADERS (bukan menimpa) — sehingga User-Agent selalu terisi
    meski caller hanya menambah satu header khusus.
    """
    caller_headers = kwargs.pop("headers", {})
    merged_headers = {**DEFAULT_HEADERS, **caller_headers}
    kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
    return httpx.AsyncClient(headers=merged_headers, **kwargs)


class ToolConfigError(ValueError):
    """Dilempar saat tool butuh API key/setting yang belum diisi di dashboard."""
