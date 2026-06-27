"""
main.py

Entrypoint utama. Menjalankan:
  1. XiaozhiClient (outbound WSS ke cloud XiaoZhi) — koneksi UTAMA
  2. Dashboard (UI manajemen + REST API) — default dengar di semua
     interface (0.0.0.0) supaya bisa diakses dari device lain di LAN;
     bisa dikunci ke "127.0.0.1" lewat Settings kalau mau localhost-only.
     CATATAN: dashboard ini tidak punya autentikasi sama sekali.
  3. MCP inbound server (opsional, untuk koneksi lokal/LAN) — jika diaktifkan

Supervisor loop: kalau network settings berubah via dashboard, listener
(2) dan (3) di-restart tanpa mematikan proses Python atau memutus koneksi
XiaoZhi yang sedang aktif.
"""

from __future__ import annotations

import asyncio
import signal
import sys
from pathlib import Path

import uvicorn

from core.config import config
from core.logger import get_logger, setup_logging
from core.netinfo import detect_lan_ip
from core.state import state
from integrations import telegram_bot, xiaozhi_client
from mcp.tools import setup_all_tools
from webapp.dashboard_app import create_dashboard_app
from webapp.mcp_app import create_mcp_app

logger = get_logger("main")

_shutdown_requested = False


def _install_signal_handlers() -> None:
    def _handle(signum, _frame):
        global _shutdown_requested
        logger.info("Sinyal %s diterima, menghentikan server...", signum)
        _shutdown_requested = True
        if state.dashboard_server is not None:
            state.dashboard_server.should_exit = True
        if state.mcp_server is not None:
            state.mcp_server.should_exit = True

    signal.signal(signal.SIGINT, _handle)
    try:
        signal.signal(signal.SIGTERM, _handle)
    except (AttributeError, ValueError):
        pass


def _build_server(app, host: str, port: int, level: str,
                   ssl_certfile: str | None = None,
                   ssl_keyfile: str | None = None) -> uvicorn.Server:
    cfg = uvicorn.Config(
        app, host=host, port=port, log_level=level.lower(),
        ssl_certfile=ssl_certfile or None,
        ssl_keyfile=ssl_keyfile or None,
    )
    return uvicorn.Server(cfg)


def _resolve_tls(net: dict) -> tuple[str | None, str | None]:
    if not net.get("use_tls"):
        return None, None
    cert, key = net.get("tls_cert_path", ""), net.get("tls_key_path", "")
    if not cert or not key:
        logger.warning("use_tls aktif tapi cert/key kosong — jalan tanpa TLS")
        return None, None
    if not Path(cert).is_file() or not Path(key).is_file():
        logger.warning("File TLS tidak ditemukan (%s / %s) — jalan tanpa TLS", cert, key)
        return None, None
    return cert, key


async def _serve_forever() -> None:
    """Loop supervisor: restart listener jaringan kalau config berubah."""
    while True:
        cfg = config.all()
        net = cfg["network"]
        level = cfg.get("logging", {}).get("level", "INFO")
        state.restart_requested = False

        # Dashboard (selalu jalan)
        dashboard_app = create_dashboard_app()
        d_server = _build_server(dashboard_app, net["dashboard_host"], net["dashboard_port"], level)
        state.dashboard_server = d_server

        # Inbound MCP server (opsional)
        servers_to_run = [d_server]
        if net.get("inbound_mcp_enabled", False):
            cert, key = _resolve_tls(net)
            mcp_app = create_mcp_app()
            m_server = _build_server(
                mcp_app, net["inbound_mcp_host"], net["inbound_mcp_port"], level, cert, key
            )
            state.mcp_server = m_server
            servers_to_run.append(m_server)
            scheme = "wss" if cert else "ws"
            logger.info("MCP inbound: %s://%s:%s%s",
                        scheme, net["inbound_mcp_host"],
                        net["inbound_mcp_port"], net.get("inbound_mcp_ws_path", "/mcp"))
        else:
            state.mcp_server = None

        logger.info("Dashboard: http://%s:%s", net["dashboard_host"], net["dashboard_port"])
        if net["dashboard_host"] in ("0.0.0.0", "::"):
            lan_ip = detect_lan_ip()
            if lan_ip:
                logger.info(
                    "  → bisa diakses dari device lain di jaringan yang sama: http://%s:%s",
                    lan_ip, net["dashboard_port"],
                )
            else:
                logger.warning(
                    "  → IP LAN tidak terdeteksi otomatis. Cek manual dengan 'ip addr' "
                    "(Termux) atau 'ipconfig' (Windows) untuk tahu alamat yang dipakai "
                    "device lain."
                )
            logger.warning(
                "  → dashboard ini TIDAK punya password. Siapa pun di jaringan/WiFi yang "
                "sama bisa membuka Settings. Kunci ke 127.0.0.1 di Settings → Jaringan "
                "kalau jaringan ini tidak dipercaya."
            )

        try:
            await asyncio.gather(*[s._serve() for s in servers_to_run])
        except OSError as exc:
            logger.error("Gagal bind port: %s — ubah port di Settings", exc)
            return

        if _shutdown_requested:
            logger.info("Server dihentikan.")
            return
        if not state.restart_requested:
            logger.warning("Listener berhenti tanpa permintaan restart, keluar.")
            return

        logger.info("Menerapkan setting jaringan baru...")


async def _async_main() -> None:
    # 1. Daftarkan semua tool
    setup_all_tools()

    # 2. Kirim notifikasi Telegram startup
    await telegram_bot.notify_startup()

    # 3. Jalankan XiaoZhi outbound client sebagai background task
    await xiaozhi_client.start()

    # 4. Jalankan bot Telegram (opsional)
    telegram_bot.start_background_task()

    try:
        # 5. Supervisor loop untuk dashboard + inbound MCP
        await _serve_forever()
    finally:
        # Cleanup saat shutdown
        await xiaozhi_client.stop()
        telegram_bot.stop_background_task()


def main() -> None:
    cfg = config.all()
    setup_logging(cfg.get("logging", {}).get("level", "INFO"))
    logger.info("xiaozhi-mcp-console v%s memulai...", cfg["meta"]["version"])
    _install_signal_handlers()

    try:
        asyncio.run(_async_main())
    except KeyboardInterrupt:
        pass
    logger.info("Selesai.")


if __name__ == "__main__":
    if sys.version_info < (3, 10):
        print("Python 3.10+ dibutuhkan.", file=sys.stderr)
        sys.exit(1)
    main()
