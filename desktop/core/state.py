"""
core/state.py — runtime state: uptime, koneksi XiaoZhi, riwayat tool call.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Literal, Optional


# ── Status koneksi outbound XiaoZhi ──────────────────────────────────────────

XiaozhiStatus = Literal["disconnected", "connecting", "connected", "error"]


@dataclass
class XiaozhiConnectionState:
    status: XiaozhiStatus = "disconnected"
    wss_url: str = ""          # URL aktif (tanpa token) untuk ditampilkan di UI
    connected_at: Optional[float] = None
    disconnected_at: Optional[float] = None
    last_error: str = ""
    reconnect_count: int = 0
    next_reconnect_in: float = 0.0   # detik sampai reconnect berikutnya
    last_method: str = ""
    last_activity_at: Optional[float] = None
    messages_received: int = 0

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "wss_url": self.wss_url,
            "connected_at": self.connected_at,
            "disconnected_at": self.disconnected_at,
            "last_error": self.last_error,
            "reconnect_count": self.reconnect_count,
            "next_reconnect_in": round(self.next_reconnect_in, 1),
            "last_method": self.last_method,
            "last_activity_at": self.last_activity_at,
            "messages_received": self.messages_received,
        }


# ── Koneksi MCP inbound (opsional, port lokal) ───────────────────────────────

@dataclass
class McpConnection:
    conn_id: int
    remote: str
    connected_at: float = field(default_factory=time.time)
    last_method: str = ""
    last_seen: float = field(default_factory=time.time)


class RuntimeState:
    def __init__(self, max_call_history: int = 200):
        self.process_started_at = time.time()

        # XiaoZhi outbound connection
        self.xiaozhi = XiaozhiConnectionState()
        # Sinyal untuk force-reconnect dari dashboard (tombol "Reconnect")
        self.xiaozhi_reconnect_requested = False
        # Referensi ke XiaozhiClient supaya route API bisa periksa state-nya
        self.xiaozhi_client = None

        # Inbound MCP connections (dari port lokal, opsional)
        self._connections: dict[int, McpConnection] = {}
        self._next_conn_id = 1

        # Tool call history
        self.call_history: Deque[dict] = deque(maxlen=max_call_history)
        self.tool_call_count = 0
        self.tool_error_count = 0

        # Restart listener dashboard/inbound-MCP
        self.restart_requested = False
        self.dashboard_server = None
        self.mcp_server = None

    def resize_history(self, capacity: int) -> None:
        self.call_history = deque(self.call_history, maxlen=capacity)

    # ── Inbound MCP connections ───────────────────────────────────────────
    def register_connection(self, remote: str) -> int:
        conn_id = self._next_conn_id
        self._next_conn_id += 1
        self._connections[conn_id] = McpConnection(conn_id=conn_id, remote=remote)
        return conn_id

    def touch_connection(self, conn_id: int, method: str) -> None:
        conn = self._connections.get(conn_id)
        if conn:
            conn.last_method = method
            conn.last_seen = time.time()

    def drop_connection(self, conn_id: int) -> None:
        self._connections.pop(conn_id, None)

    def list_inbound_connections(self) -> list[dict]:
        return [
            {
                "id": c.conn_id,
                "remote": c.remote,
                "connected_at": c.connected_at,
                "last_method": c.last_method,
                "last_seen": c.last_seen,
            }
            for c in self._connections.values()
        ]

    # ── Tool call history ─────────────────────────────────────────────────
    def record_call(self, tool_name: str, arguments: dict, ok: bool,
                    duration_ms: float, error: Optional[str] = None,
                    result_preview: Optional[str] = None) -> None:
        self.tool_call_count += 1
        if not ok:
            self.tool_error_count += 1
        self.call_history.append({
            "time": time.time(),
            "tool": tool_name,
            "arguments": arguments,
            "ok": ok,
            "duration_ms": round(duration_ms, 1),
            "error": error,
            "result_preview": result_preview,
        })

    def uptime_seconds(self) -> float:
        return time.time() - self.process_started_at


state = RuntimeState()
