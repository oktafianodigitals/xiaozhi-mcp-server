"""
mcp/server.py

Registry tool MCP — setara `McpServer::tools_` di firmware (Arah 1), tapi
sebagai dict (lookup-by-name lebih sering dipakai daripada iterasi
berurutan) dan dengan filter enable/disable yang dibaca live dari
core.config supaya toggle di dashboard berlaku tanpa restart proses.
"""

from __future__ import annotations

import time
from typing import Any

from core.config import config
from core.logger import get_logger
from core.state import state
from mcp.schema import Tool

logger = get_logger("mcp.registry")


class McpToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, name: str, description: str, input_schema: dict,
                 handler, category: str = "general") -> None:
        if name in self._tools:
            # Setara perilaku McpServer::AddTool di firmware: nama duplikat
            # tidak crash, hanya diabaikan dengan warning.
            logger.warning("Tool '%s' sudah terdaftar, registrasi diabaikan", name)
            return
        self._tools[name] = Tool(name, description, input_schema, handler, category)
        logger.debug("Tool terdaftar: %s [%s]", name, category)

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def all_tools(self) -> list[Tool]:
        return list(self._tools.values())

    def is_enabled(self, name: str) -> bool:
        return bool(config.get("tools_enabled", name, default=True))

    def list_tools(self) -> list[dict]:
        """Dipanggil saat client cloud mengirim tools/list — hanya tool yang
        enabled di settings yang dikirim ke LLM."""
        return [t.to_dict() for t in self._tools.values() if self.is_enabled(t.name)]

    def list_tools_with_status(self) -> list[dict]:
        """Dipakai dashboard (halaman Tools) — tampilkan semua tool + status
        enabled-nya, terlepas dari filter."""
        return [
            {**t.to_dict(), "category": t.category, "enabled": self.is_enabled(t.name)}
            for t in self._tools.values()
        ]

    async def call(self, name: str, arguments: dict) -> Any:
        if name not in self._tools:
            raise LookupError(f"Unknown tool: {name}")
        if not self.is_enabled(name):
            raise LookupError(f"Tool '{name}' dinonaktifkan di dashboard settings")

        tool = self._tools[name]
        started = time.perf_counter()
        try:
            result = await tool.handler(arguments)
            duration_ms = (time.perf_counter() - started) * 1000
            preview = str(result)[:200]
            state.record_call(name, arguments, True, duration_ms, result_preview=preview)
            return result
        except Exception as exc:  # noqa: BLE001 — sengaja luas, ini boundary tool eksternal
            duration_ms = (time.perf_counter() - started) * 1000
            state.record_call(name, arguments, False, duration_ms, error=str(exc))
            raise


registry = McpToolRegistry()
