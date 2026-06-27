"""
integrations/xiaozhi_client.py

Koneksi outbound ke cloud XiaoZhi lewat WSS.

Alur:
  1. Client ini DIAL KELUAR ke wss://api.xiaozhi.me/mcp/?token=TOKEN
  2. XiaoZhi cloud mengirim request JSON-RPC (initialize, tools/list, tools/call)
  3. Kita balas lewat koneksi WebSocket yang sama
  4. Kalau koneksi putus: reconnect otomatis dengan exponential backoff

Perbedaan utama dari server inbound (mcp_app.py):
  - Di sini KITA yang membuka koneksi ke luar, bukan menunggu koneksi masuk.
  - Token JWT dikirim sebagai query-string di URL (sesuai API XiaoZhi).
  - Satu koneksi permanen, bukan multi-client.

State koneksi selalu tersimpan di core.state.state.xiaozhi supaya
dashboard bisa menampilkannya secara real-time.
"""

from __future__ import annotations

import asyncio
import json
import time
from urllib.parse import urlencode, urlparse, urlunparse

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from core.config import config
from core.logger import get_logger
from core.state import state
from mcp.dispatcher import handle_rpc

logger = get_logger("integrations.xiaozhi_client")


def _build_url() -> str:
    """Gabungkan base URL + token jadi URL WSS lengkap."""
    base = (config.get("xiaozhi", "wss_base_url", default="") or "").rstrip("/")
    token = (config.get("xiaozhi", "token", default="") or "").strip()
    if not base:
        return ""
    if not token:
        return base + "/"
    # Kalau base sudah mengandung "?", pakai "&token=", kalau belum pakai "?token="
    sep = "&" if "?" in base else "?"
    return f"{base}/{sep}token={token}"


def _safe_url_for_log(url: str) -> str:
    """Sembunyikan token dari URL untuk log (tampilkan 8 karakter awal token)."""
    if "token=" not in url:
        return url
    parts = url.split("token=", 1)
    tok = parts[1]
    token_preview = (tok[:6] + "..." + tok[-6:]) if len(tok) > 12 else tok
    return parts[0] + "token=" + token_preview


class XiaozhiClient:
    """Client WebSocket outbound ke cloud XiaoZhi. Dijalankan sebagai asyncio Task."""

    def __init__(self) -> None:
        self._stop_event = asyncio.Event()
        self._reconnect_event = asyncio.Event()

    def request_stop(self) -> None:
        """Diminta dari luar (main.py shutdown atau dashboard Disable)."""
        self._stop_event.set()

    def request_reconnect(self) -> None:
        """Diminta dari dashboard (tombol Reconnect)."""
        self._reconnect_event.set()

    async def run(self) -> None:
        logger.info("XiaozhiClient dimulai")
        state.xiaozhi_client = self

        delay = float(config.get("xiaozhi", "reconnect_delay_initial_s", default=3))
        delay_max = float(config.get("xiaozhi", "reconnect_delay_max_s", default=60))

        while not self._stop_event.is_set():
            # Baca config terbaru tiap iterasi (supaya perubahan token/URL berlaku)
            if not config.get("xiaozhi", "enabled", default=True):
                state.xiaozhi.status = "disconnected"
                state.xiaozhi.last_error = "Dinonaktifkan di Settings"
                logger.info("XiaozhiClient dinonaktifkan di config, idle...")
                await asyncio.sleep(5)
                continue

            url = _build_url()
            if not url or not config.get("xiaozhi", "token", default=""):
                state.xiaozhi.status = "disconnected"
                state.xiaozhi.last_error = "Token belum diatur (Settings → XiaoZhi Connection)"
                logger.warning("Token XiaoZhi kosong, menunggu config diisi...")
                await asyncio.sleep(10)
                continue

            # Tampilkan URL di state tanpa token (untuk UI)
            state.xiaozhi.wss_url = _safe_url_for_log(url)
            state.xiaozhi.status = "connecting"
            state.xiaozhi.last_error = ""
            state.xiaozhi.next_reconnect_in = 0.0
            logger.info("Mencoba konek ke %s", _safe_url_for_log(url))

            try:
                ping_interval = int(config.get("xiaozhi", "ping_interval_s", default=20))
                async with websockets.connect(
                    url,
                    ping_interval=ping_interval,
                    ping_timeout=10,
                    close_timeout=5,
                    additional_headers={"User-Agent": "xiaozhi-mcp-console/1.1.0"},
                ) as ws:
                    state.xiaozhi.status = "connected"
                    state.xiaozhi.connected_at = time.time()
                    state.xiaozhi.reconnect_count += 1 if state.xiaozhi.reconnect_count > 0 else 0
                    delay = float(config.get("xiaozhi", "reconnect_delay_initial_s", default=3))
                    logger.info("Terhubung ke XiaoZhi cloud: %s", _safe_url_for_log(url))

                    self._reconnect_event.clear()
                    await self._message_loop(ws)

            except (ConnectionClosed, WebSocketException) as exc:
                state.xiaozhi.status = "error"
                state.xiaozhi.last_error = str(exc)
                state.xiaozhi.disconnected_at = time.time()
                logger.warning("Koneksi XiaoZhi terputus: %s", exc)

            except OSError as exc:
                state.xiaozhi.status = "error"
                state.xiaozhi.last_error = f"Network error: {exc}"
                state.xiaozhi.disconnected_at = time.time()
                logger.warning("Network error ke XiaoZhi: %s", exc)

            except Exception as exc:  # noqa: BLE001
                state.xiaozhi.status = "error"
                state.xiaozhi.last_error = str(exc)
                state.xiaozhi.disconnected_at = time.time()
                logger.error("Error tidak terduga di XiaozhiClient: %s", exc, exc_info=True)

            if self._stop_event.is_set():
                break

            if not config.get("xiaozhi", "reconnect_enabled", default=True):
                state.xiaozhi.status = "disconnected"
                logger.info("Auto-reconnect dinonaktifkan, berhenti.")
                break

            state.xiaozhi.reconnect_count += 1
            state.xiaozhi.next_reconnect_in = delay
            logger.info("Reconnect ke-%d dalam %.0fs...", state.xiaozhi.reconnect_count, delay)

            # Tunggu delay ATAU sinyal reconnect manual dari dashboard
            try:
                await asyncio.wait_for(
                    self._wait_reconnect_or_stop(delay),
                    timeout=delay + 1,
                )
            except asyncio.TimeoutError:
                pass

            if self._stop_event.is_set():
                break

            # Backoff eksponensial
            delay = min(delay * 2, delay_max)
            state.xiaozhi.next_reconnect_in = 0.0

        state.xiaozhi.status = "disconnected"
        state.xiaozhi.next_reconnect_in = 0.0
        logger.info("XiaozhiClient berhenti")

    async def _wait_reconnect_or_stop(self, timeout: float) -> None:
        """Tunggu sampai: (a) reconnect manual diminta, (b) stop diminta, atau (c) timeout."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            state.xiaozhi.next_reconnect_in = max(0.0, remaining)
            if self._stop_event.is_set():
                return
            if self._reconnect_event.is_set():
                self._reconnect_event.clear()
                state.xiaozhi.next_reconnect_in = 0.0
                return
            await asyncio.sleep(0.5)

    async def _message_loop(self, ws) -> None:
        """Baca pesan dari XiaoZhi, dispatch ke handler MCP, kirim respons."""
        async for raw in ws:
            if self._stop_event.is_set() or self._reconnect_event.is_set():
                break

            state.xiaozhi.last_activity_at = time.time()
            state.xiaozhi.messages_received += 1

            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("Pesan bukan JSON dari XiaoZhi: %s", raw[:120])
                continue

            method = message.get("method", "")
            state.xiaozhi.last_method = method
            logger.debug("← XiaoZhi: %s (id=%s)", method, message.get("id"))

            try:
                response = await handle_rpc(message)
            except Exception as exc:  # noqa: BLE001
                logger.error("Dispatch error untuk '%s': %s", method, exc)
                response = {
                    "jsonrpc": "2.0",
                    "id": message.get("id"),
                    "error": {"message": f"Internal server error: {exc}"},
                }

            if response is not None:
                payload = json.dumps(response, ensure_ascii=False)
                await ws.send(payload)
                logger.debug("→ XiaoZhi: id=%s", response.get("id"))


# ── Fungsi lifecyle yang dipanggil dari main.py ───────────────────────────────

_client_task: asyncio.Task | None = None
_client_instance: XiaozhiClient | None = None


async def start() -> None:
    global _client_task, _client_instance
    if _client_task is not None and not _client_task.done():
        return
    _client_instance = XiaozhiClient()
    _client_task = asyncio.create_task(_client_instance.run(), name="xiaozhi-client")
    logger.info("XiaozhiClient task dimulai")


async def stop() -> None:
    global _client_task, _client_instance
    if _client_instance is not None:
        _client_instance.request_stop()
    if _client_task is not None and not _client_task.done():
        _client_task.cancel()
        try:
            await _client_task
        except asyncio.CancelledError:
            pass
    _client_task = None
    _client_instance = None
    state.xiaozhi.status = "disconnected"
    logger.info("XiaozhiClient dihentikan")


def reconnect() -> None:
    """Dipanggil dari route /api/xiaozhi/reconnect — reset backoff & reconnect sekarang."""
    if _client_instance is not None:
        _client_instance.request_reconnect()
        logger.info("Force reconnect diminta dari dashboard")
