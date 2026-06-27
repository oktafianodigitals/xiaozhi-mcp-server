"""
core/config.py — ConfigManager: thread-safe JSON config dengan deep merge,
atomic write, dan secret masking.
"""

from __future__ import annotations

import copy
import json
import os
import threading
from pathlib import Path
from typing import Any

from core.defaults import DEFAULT_CONFIG

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "settings.json"

# Path ke field rahasia — dimasking di response GET /api/config.
_SECRET_PATHS = {
    ("api_keys", "web_search", "api_key"),
    ("api_keys", "news",       "api_key"),
    ("api_keys", "youtube",    "api_key"),
    ("api_keys", "translate",  "api_key"),
    ("telegram", "bot_token"),
    ("xiaozhi",  "token"),
}


def _deep_merge(base: dict, override: dict) -> dict:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _mask(value: str) -> str:
    """Mask string rahasia. JWT yang panjang: tampilkan 6 karakter awal + ... + 6 akhir."""
    if not value:
        return ""
    if len(value) <= 12:
        return value[:2] + "*" * (len(value) - 4) + value[-2:]
    # Format JWT-friendly: eyJhbG...SSMMQ
    return value[:6] + "..." + value[-6:]


class ConfigManager:
    def __init__(self, path: Path = CONFIG_PATH):
        self._path = path
        self._lock = threading.Lock()
        self._data: dict = {}
        self.load()

    def load(self) -> dict:
        with self._lock:
            if self._path.exists():
                try:
                    with open(self._path, "r", encoding="utf-8") as f:
                        on_disk = json.load(f)
                except (json.JSONDecodeError, OSError):
                    on_disk = {}
                self._data = _deep_merge(DEFAULT_CONFIG, on_disk)
            else:
                self._data = copy.deepcopy(DEFAULT_CONFIG)
            self._save_locked()
            return copy.deepcopy(self._data)

    def _save_locked(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, self._path)

    def save(self) -> None:
        with self._lock:
            self._save_locked()

    def all(self) -> dict:
        with self._lock:
            return copy.deepcopy(self._data)

    def all_masked(self) -> dict:
        data = self.all()
        for path in _SECRET_PATHS:
            node = data
            for key in path[:-1]:
                node = node.setdefault(key, {})
            last = path[-1]
            if last in node and node[last]:
                node[last] = _mask(node[last])
        return data

    def get(self, *path: str, default: Any = None) -> Any:
        with self._lock:
            node: Any = self._data
            for key in path:
                if not isinstance(node, dict) or key not in node:
                    return default
                node = node[key]
            return copy.deepcopy(node)

    def update(self, partial: dict) -> dict:
        with self._lock:
            self._strip_masked_secrets(partial, prefix=())
            self._data = _deep_merge(self._data, partial)
            self._save_locked()
            return copy.deepcopy(self._data)

    def _strip_masked_secrets(self, node: dict, prefix: tuple) -> None:
        for key, value in list(node.items()):
            path = prefix + (key,)
            if isinstance(value, dict):
                self._strip_masked_secrets(value, path)
            elif path in _SECRET_PATHS and isinstance(value, str) and ("*" in value or "..." in value):
                del node[key]

    def set_path(self, path: tuple, value: Any) -> None:
        with self._lock:
            node = self._data
            for key in path[:-1]:
                node = node.setdefault(key, {})
            node[path[-1]] = value
            self._save_locked()


config = ConfigManager()
