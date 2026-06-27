"""
core/logger.py

Setup logging terpusat:
- Console handler (stdout) — supaya tetap kelihatan di terminal/Termux.
- RotatingFileHandler — disimpan di logs/app.log, maks 1MB x 3 file.
- RingBufferHandler — menyimpan N log terakhir di memori, dibaca oleh
  dashboard (halaman Logs) lewat GET /api/logs. Tidak perlu database
  terpisah hanya untuk menampilkan log.
"""

from __future__ import annotations

import logging
import logging.handlers
from collections import deque
from pathlib import Path
from typing import Deque

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "app.log"

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-22s | %(message)s"


class RingBufferHandler(logging.Handler):
    def __init__(self, capacity: int = 500):
        super().__init__()
        self.capacity = capacity
        self.buffer: Deque[dict] = deque(maxlen=capacity)

    def resize(self, capacity: int) -> None:
        self.capacity = capacity
        self.buffer = deque(self.buffer, maxlen=capacity)

    def emit(self, record: logging.LogRecord) -> None:
        self.buffer.append({
            "time": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        })

    def formatTime(self, record: logging.LogRecord) -> str:
        return self.formatter.formatTime(record, "%Y-%m-%d %H:%M:%S") if self.formatter else str(record.created)

    def get_logs(self, level: str | None = None, limit: int = 200) -> list[dict]:
        items = list(self.buffer)
        if level:
            items = [i for i in items if i["level"] == level.upper()]
        return items[-limit:]


ring_handler = RingBufferHandler()


def setup_logging(level: str = "INFO") -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(_LOG_FORMAT)

    root = logging.getLogger()
    root.setLevel(level.upper())
    root.handlers.clear()

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    ring_handler.setFormatter(formatter)
    root.addHandler(ring_handler)

    # uvicorn access log cukup berisik untuk dashboard kecil, turunkan levelnya
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    # httpx/httpcore log URL request LENGKAP di level INFO (termasuk token
    # Telegram bot yang ada di URL, contoh: api.telegram.org/bot<TOKEN>/...).
    # Log ini masuk ke logs/app.log DAN ke RingBufferHandler yang dibaca
    # halaman Logs dashboard — sekarang dashboard bisa diakses dari LAN,
    # jadi token itu bisa leak ke siapa pun yang buka halaman Logs.
    # Turunkan ke WARNING supaya request normal tidak ikut tercatat.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
