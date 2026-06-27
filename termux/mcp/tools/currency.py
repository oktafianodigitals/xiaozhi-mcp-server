"""
mcp/tools/currency.py

currency.convert — pakai Frankfurter API (data ECB), tidak butuh API key.
Catatan: Frankfurter tidak punya data IDR setiap hari di semua kasus, tapi
umumnya tersedia untuk mata uang utama. Kalau provider ini tidak punya
pasangan mata uang yang diminta, error akan menyebutkan dengan jelas.

Frankfurter migrasi domain dari api.frankfurter.app ke api.frankfurter.dev
(v1) pertengahan 2026 — URL lama masih hidup tapi 301 redirect permanen ke
domain baru, jadi kita pakai domain baru langsung di sini.
"""

from __future__ import annotations

from mcp.server import registry
from mcp.tools._http import client

FRANKFURTER_URL = "https://api.frankfurter.dev/v1/latest"  # migrasi dari .app per pertengahan 2026


async def convert(arguments: dict) -> dict:
    from_currency = (arguments.get("from_currency") or "").strip().upper()
    to_currency = (arguments.get("to_currency") or "").strip().upper()
    amount = arguments.get("amount")

    if len(from_currency) != 3 or len(to_currency) != 3:
        raise ValueError("'from_currency' dan 'to_currency' harus kode ISO 4217 3 huruf, contoh 'USD'")
    if not isinstance(amount, (int, float)) or amount <= 0:
        raise ValueError("'amount' harus angka lebih besar dari 0")

    async with client() as http:
        resp = await http.get(FRANKFURTER_URL, params={
            "amount": amount, "from": from_currency, "to": to_currency,
        })
    if resp.status_code == 422:
        raise ValueError(f"Pasangan mata uang {from_currency}->{to_currency} tidak didukung provider")
    resp.raise_for_status()
    data = resp.json()
    rates = data.get("rates", {})
    if to_currency not in rates:
        raise ValueError(f"Tidak ada kurs untuk {to_currency}")

    return {
        "from": from_currency, "to": to_currency,
        "amount": amount, "converted": rates[to_currency],
        "date": data.get("date"),
    }


def setup() -> None:
    registry.register(
        name="currency.convert",
        description="Mengonversi nominal dari satu mata uang ke mata uang lain dengan kurs terkini.",
        input_schema={
            "type": "object",
            "properties": {
                "from_currency": {"type": "string", "pattern": "^[A-Za-z]{3}$", "description": "Kode ISO 4217 asal, contoh 'USD'"},
                "to_currency": {"type": "string", "pattern": "^[A-Za-z]{3}$", "description": "Kode ISO 4217 tujuan, contoh 'IDR'"},
                "amount": {"type": "number", "exclusiveMinimum": 0, "description": "Jumlah yang dikonversi"},
            },
            "required": ["from_currency", "to_currency", "amount"],
        },
        handler=convert,
        category="info_search",
    )
