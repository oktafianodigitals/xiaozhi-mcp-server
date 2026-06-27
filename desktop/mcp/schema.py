"""
mcp/schema.py

Definisi struktur Tool — setara `PropertyList` di firmware ESP32 (Arah 1),
tapi pakai JSON Schema penuh karena tidak ada batasan tipe bool/int/string
seperti di device.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict
    handler: Callable[[dict], Awaitable[Any]]
    category: str = "general"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }
