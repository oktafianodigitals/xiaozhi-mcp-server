# xiaozhi-mcp-console  v1.1

Server Python MCP (Model Context Protocol) yang **connect keluar** ke cloud XiaoZhi lewat WSS permanen. Dashboard web dark-theme untuk mengatur token, URL endpoint, API key tool, dan melihat status koneksi real-time — tanpa perlu menyentuh file config.

```
  ┌─────────────────────────────────────────────────────────────┐
  │  xiaozhi-mcp-console (server Python ini)                    │
  │                                                             │
  │  XiaozhiClient ──WSS outbound──► wss://api.xiaozhi.me/mcp/ │
  │  (koneksi UTAMA)                  ?token=JWT                │
  │                                                             │
  │  Dashboard UI   ◄──────────────── http://localhost:8766     │
  │  (setting, status, logs)                                    │
  └─────────────────────────────────────────────────────────────┘
```

Server ini **dial keluar** ke XiaoZhi — tidak perlu port forward atau IP publik.
XiaoZhi cloud mengirim request `tools/list` / `tools/call` lewat koneksi yang sama.

---

## Quick Start

### Linux / macOS / Termux
```bash
git clone https://github.com/oktafianodigitals/xiaozhi-mcp-server.git
cd xiaozhi-mcp-server/termux
chmod +x start.sh && ./start.sh
```

### Windows
Double-click **`start.bat`** atau dari CMD:
```
cd xiaozhi-mcp-server/desktop
start.bat
```

Buka browser: **`http://127.0.0.1:8766`**

---

## Setup Token XiaoZhi (langkah pertama)

1. Login ke console XiaoZhi → **Settings → MCP Endpoint**
2. Salin URL endpoint WSS, contoh:
   ```
   wss://api.xiaozhi.me/mcp/?token=eyJhbGci...
   ```
3. Buka dashboard → **Settings → ☁️ XiaoZhi Cloud — MCP Endpoint**
4. Isi **Base URL**: `wss://api.xiaozhi.me/mcp/`
5. Isi **Token JWT**: paste token panjang dari console XiaoZhi
6. Klik **Simpan & Reconnect**
7. Lihat status di halaman **Status** — harus berubah menjadi `Terhubung` dalam beberapa detik

> Token disimpan di `config/settings.json`. Di UI hanya ditampilkan 6 karakter awal + `...` + 6 karakter akhir (`eyJhbG...gSSMMQ`) — token lengkap tidak pernah muncul di browser, response API, maupun log server.

---

## Fitur

| Tool | Provider | API Key? |
|---|---|---|
| `weather.get_forecast` | Open-Meteo | ✗ keyless |
| `wiki.lookup` | Wikipedia REST | ✗ keyless |
| `currency.convert` | Frankfurter/ECB | ✗ keyless |
| `web.search` | Brave Search API | ✓ |
| `news.search` | NewsAPI.org | ✓ |
| `translate.text` | LibreTranslate | △ opsional |
| `youtube.search_music` | YouTube Data API v3 | ✓ |
| `youtube.search_video` | YouTube Data API v3 | ✓ |
| `youtube.play_music` | — (buka browser lokal) | ✗ keyless |
| `youtube.play_video` | — (buka browser lokal) | ✗ keyless |
| `telegram.send_message` | Telegram Bot API | ✓ |

> `youtube.play_music` / `youtube.play_video` tidak memanggil API apa pun — keduanya membuka video
> langsung di browser perangkat tempat server berjalan. Lihat bagian **"Memutar video — Windows vs Termux"**
> di bawah untuk detail perilaku per-platform.

---

## Memutar video — Windows vs Termux

`youtube.play_music` dan `youtube.play_video` membuka video YouTube di browser perangkat tempat
**server ini berjalan** (bukan di perangkat tempat LLM/XiaoZhi berada). Server mendeteksi platform
otomatis saat runtime dan memilih strategi yang sesuai — tidak ada konfigurasi yang perlu diganti manual:

**Windows / desktop lain**
Server men-spawn proses `brave.exe` langsung dengan URL video. Lokasi `brave.exe` dicari otomatis
(lokasi instalasi umum di Program Files/AppData), atau bisa diisi manual di dashboard
**Settings → Browser** kalau auto-detect gagal (instalasi di drive/folder non-standar).

**Termux (Android)**
Brave di Android adalah APK, bukan binary yang bisa dijalankan lewat command line — jadi strategi
di atas tidak berlaku. Server malah memanggil `termux-open-url <url>`, yang memicu Android Intent
(`ACTION_VIEW`) ke **browser default** sistem Android. Ini berarti:

- Browser yang terbuka adalah apa pun yang diset sebagai default di **Android Settings → Apps →
  Default apps → Browser app** — bukan otomatis Brave, kecuali Brave memang sudah diset default.
- Field path Brave di Settings dashboard **diabaikan** sepenuhnya di jalur ini.
- Wajib terinstall lebih dulu:
  1. `pkg install termux-api` (paket command-line di Termux)
  2. App pendamping **Termux:API** dari F-Droid atau Play Store (tanpa app ini, `termux-open-url`
     akan gagal/timeout meski paketnya sudah terpasang)
- Gunakan tombol **"Test deteksi"** di Settings → Browser untuk memastikan `termux-open-url`
  tersedia sebelum mencoba tool ini lewat XiaoZhi.

---

## Dashboard

| Halaman | Fungsi |
|---|---|
| **Status** | Status koneksi XiaoZhi (live), uptime, riwayat tool call |
| **Tools** | Aktif/nonaktifkan tool per-item, tombol Test |
| **Settings** | Token XiaoZhi, API key, jaringan, Telegram |
| **Logs** | 500 baris log terakhir, filter per level |

### Signal Strip
Di bagian atas setiap halaman:
```
[ XiaoZhi Cloud ] ~~~~ [ MCP Console ] ~~~~ [ Tools Aktif ]
```
Gelombang beranimasi saat koneksi aktif, berhenti saat disconnected.

---

## Arsitektur Koneksi

```
Internet
   │
   ▼
wss://api.xiaozhi.me/mcp/?token=JWT
   ▲
   │  (koneksi keluar dari server ini)
   │
XiaozhiClient (asyncio Task)
   │   • Auto-reconnect dengan exponential backoff
   │   • Ping/keepalive tiap 20 detik
   │   • Force reconnect dari dashboard (tanpa restart)
   │
McpDispatcher
   │   • initialize → kirim serverInfo
   │   • tools/list → kirim daftar tool yang enabled
   │   • tools/call → eksekusi tool, kirim hasil
   │
McpToolRegistry ──── 10 tool modules
```

Keunggulan pola outbound ini:
- **Tidak perlu IP publik / port forward** — cocok untuk server di balik NAT, Termux, atau VPN
- **Tidak ada permukaan serangan inbound** — tidak ada port yang perlu dibuka ke internet
- **Auto-reconnect transparan** — client cloud tidak perlu tahu kalau koneksi sempat putus

---

## Reconnect Otomatis

Saat koneksi putus (network error, timeout, server restart):
1. Client menunggu `reconnect_delay_initial_s` detik (default: 3)
2. Retry — kalau gagal, delay × 2
3. Terus sampai `reconnect_delay_max_s` (default: 60 detik)
4. Status tampil live di dashboard dan signal strip

Dari dashboard, klik **⟳ Reconnect** untuk paksa reconnect segera (reset backoff).

---

## Memperbarui Token

Kalau token expired (dapat dari console XiaoZhi):
1. Buka **Settings → ☁️ XiaoZhi Cloud**
2. Paste token baru di kolom Token JWT
3. Klik **Simpan & Reconnect**

**Tidak perlu restart server.** Koneksi lama diputus dan koneksi baru dengan token baru dibuat dalam hitungan detik.

---

## Menambah Tool Baru

1. Buat `mcp/tools/nama_tool.py` dengan fungsi `setup()` dan `async handler(args) -> dict`
2. Daftarkan di `mcp/tools/__init__.py` → tambah ke `_ALL_MODULES`
3. Restart server — tool muncul otomatis di dashboard `/tools`

Lihat `mcp/tools/weather.py` sebagai contoh tool keyless.

---

## Struktur File

```
xiaozhi-mcp-console/
├── main.py                          # Entrypoint: supervisor dual-server
├── requirements.txt                 # Dependency Python
├── start.sh / start.bat             # Launcher cross-platform
│
├── core/
│   ├── config.py                    # ConfigManager (JSON, atomic write, masking)
│   ├── defaults.py                  # Skema config default (termasuk xiaozhi.*)
│   ├── logger.py                    # Logging: file + console + RingBuffer
│   └── state.py                     # RuntimeState + XiaozhiConnectionState
│
├── integrations/
│   ├── xiaozhi_client.py            # ★ Outbound WSS client ke XiaoZhi cloud
│   ├── telegram_api.py              # Wrapper Telegram Bot API
│   └── telegram_bot.py             # Bot background: /status /help
│
├── mcp/
│   ├── dispatcher.py                # JSON-RPC 2.0 handler MCP
│   ├── server.py                    # McpToolRegistry
│   ├── schema.py                    # Dataclass Tool
│   └── tools/
│       ├── __init__.py              # setup_all_tools()
│       ├── weather.py  wiki.py  currency.py   # keyless
│       ├── web_search.py  news.py  translate.py  # butuh API key
│       ├── youtube_search_music.py  # youtube.search_music (+ helper _search)
│       ├── youtube_search_video.py  # youtube.search_video
│       ├── youtube_play_music.py    # youtube.play_music
│       └── telegram_tool.py         # telegram.send_message
│
├── webapp/
│   ├── dashboard_app.py             # FastAPI dashboard
│   ├── mcp_app.py                   # FastAPI MCP inbound (opsional)
│   ├── routes_pages.py              # HTML pages (Jinja2)
│   ├── routes_api.py                # REST /api/*
│   ├── static/css/style.css         # Dark theme
│   ├── static/js/dashboard.js       # Vanilla JS, live polling
│   └── templates/                   # base, index, settings, tools, logs
│
├── config/settings.json             # ← dibuat otomatis, JANGAN dicommit!
└── logs/app.log                     # Log file berputar (3×1MB)
```

---

## Troubleshooting

| Masalah | Solusi |
|---|---|
| Status "Token belum diatur" | Buka Settings, isi token JWT dari console XiaoZhi |
| Status "error" terus | Cek token belum expired di console XiaoZhi; kalau expired, perbarui token |
| Dashboard tidak terbuka | Pastikan port 8766 tidak dipakai proses lain (`lsof -i:8766` / `netstat -ano`) |
| Termux: server mati saat HP lock | Jalankan `termux-wake-lock` dulu, gunakan `tmux` untuk session persisten |
| Windows: `python` tidak dikenal | Install Python dari python.org, centang "Add to PATH" |

---

## Lisensi

MIT
