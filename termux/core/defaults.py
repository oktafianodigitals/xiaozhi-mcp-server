"""
core/defaults.py  — skema konfigurasi default.
"""

DEFAULT_CONFIG = {
    "meta": {
        "server_name": "xiaozhi-mcp-console",
        "version": "1.2.0",
    },

    # ── Koneksi keluar ke cloud XiaoZhi ──────────────────────────────────
    # Ini adalah koneksi UTAMA: server kita yang dial keluar ke WSS XiaoZhi.
    # XiaoZhi mengirim request MCP (tools/list, tools/call) lewat koneksi ini.
    "xiaozhi": {
        "enabled": True,
        # URL lengkap tanpa token — token disimpan terpisah supaya mudah diperbarui
        # tanpa mengganti seluruh URL.
        "wss_base_url": "wss://api.xiaozhi.me/mcp/",
        # JWT token dari console XiaoZhi (Settings > MCP Endpoint)
        "token": "",
        # Reconnect: backoff eksponensial, dimulai dari delay_initial_s
        "reconnect_enabled": True,
        "reconnect_delay_initial_s": 3,
        "reconnect_delay_max_s": 60,
        # Heartbeat ping supaya koneksi tidak diputus oleh proxy/firewall
        "ping_interval_s": 20,
    },

    # ── Dashboard (UI manajemen) ───────────────────────────────────────────
    # dashboard_host default "0.0.0.0" → bisa diakses dari device lain di
    # jaringan yang sama (laptop, HP lain) pakai IP LAN server, bukan cuma
    # 127.0.0.1. PERHATIAN: dashboard ini TIDAK punya login/password, jadi
    # siapa pun yang konek ke jaringan/WiFi/hotspot yang sama bisa membuka
    # Settings. Kalau server ini jalan di jaringan yang tidak dipercaya,
    # ubah ke "127.0.0.1" supaya hanya bisa diakses dari device ini sendiri.
    "network": {
        "dashboard_host": "0.0.0.0",
        "dashboard_port": 8766,
        # Server MCP inbound (opsional, untuk koneksi lokal/LAN tanpa token)
        "inbound_mcp_enabled": False,
        "inbound_mcp_host": "0.0.0.0",
        "inbound_mcp_port": 8765,
        "inbound_mcp_ws_path": "/mcp",
        "use_tls": False,
        "tls_cert_path": "",
        "tls_key_path": "",
    },

    # ── Tool enable/disable ───────────────────────────────────────────────
    "tools_enabled": {
        "web.search": True,
        "weather.get_forecast": True,
        "news.search": True,
        "wiki.lookup": True,
        "currency.convert": True,
        "translate.text": True,
        "youtube.search_music": True,
        "youtube.play_music": True,
        "youtube.search_video": True,
        "youtube.play_video": True,
        "telegram.send_message": True,
    },

    # ── Browser lokal (dipakai youtube.play_music / youtube.play_video) ───
    # Server ini didesain jalan lokal di mesin yang sama dengan browser
    # (lihat start.bat). brave_path biasanya TIDAK perlu diisi manual —
    # auto-detect akan mencoba lokasi instalasi umum Windows dulu. Isi ini
    # hanya kalau auto-detect gagal (instalasi Brave non-standar / drive lain).
    "browser": {
        "brave_path": "",
    },

    # ── API key per provider ──────────────────────────────────────────────
    "api_keys": {
        "web_search": {"provider": "brave", "api_key": ""},
        "news":       {"api_key": ""},
        "youtube":    {"api_key": ""},
        "translate":  {"endpoint": "https://libretranslate.com", "api_key": ""},
    },

    # ── Telegram ─────────────────────────────────────────────────────────
    "telegram": {
        "bot_token": "",
        "default_chat_id": "",
        "bot_enabled": False,
        "notify_on_start": True,
        "notify_on_tool_error": False,
    },

    "logging": {
        "level": "INFO",
        "max_log_entries": 500,
        "max_call_history": 200,
    },
}
