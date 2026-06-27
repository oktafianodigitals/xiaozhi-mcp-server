"""
mcp/tools/weather.py

weather.get_forecast — pakai Open-Meteo (geocoding + forecast), TIDAK
butuh API key sama sekali. Dipilih sebagai default supaya tool ini langsung
jalan begitu server pertama kali dinyalakan, tanpa user harus daftar API
dulu.
"""

from __future__ import annotations

from mcp.server import registry
from mcp.tools._http import client

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

_WEATHER_CODE_ID = {
    0: "cerah", 1: "cerah berawan sebagian", 2: "berawan sebagian", 3: "berawan tebal",
    45: "berkabut", 48: "kabut beku", 51: "gerimis ringan", 53: "gerimis", 55: "gerimis lebat",
    61: "hujan ringan", 63: "hujan", 65: "hujan lebat", 71: "salju ringan", 73: "salju",
    75: "salju lebat", 80: "hujan lokal ringan", 81: "hujan lokal", 82: "hujan lokal lebat",
    95: "badai petir", 96: "badai petir + es ringan", 99: "badai petir + es lebat",
}


async def get_forecast(arguments: dict) -> dict:
    city = (arguments.get("city") or "").strip()
    if not city:
        raise ValueError("Parameter 'city' tidak boleh kosong")
    if len(city) > 80:
        raise ValueError("Parameter 'city' terlalu panjang (maksimal 80 karakter)")

    days = arguments.get("days", 1)
    if not isinstance(days, int) or not (1 <= days <= 7):
        raise ValueError("Parameter 'days' harus berupa angka 1-7")

    async with client() as http:
        geo_resp = await http.get(GEOCODE_URL, params={"name": city, "count": 1, "language": "id"})
        geo_resp.raise_for_status()
        results = geo_resp.json().get("results") or []
        if not results:
            raise ValueError(f"Kota '{city}' tidak ditemukan")
        place = results[0]
        lat, lon = place["latitude"], place["longitude"]
        label = f"{place.get('name', city)}, {place.get('country', '')}".strip(", ")

        fc_resp = await http.get(FORECAST_URL, params={
            "latitude": lat, "longitude": lon,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weathercode",
            "timezone": "auto", "forecast_days": days,
        })
        fc_resp.raise_for_status()
        daily = fc_resp.json().get("daily", {})

    forecast = []
    for i, date in enumerate(daily.get("time", [])):
        code = daily.get("weathercode", [None])[i] if i < len(daily.get("weathercode", [])) else None
        forecast.append({
            "date": date,
            "condition": _WEATHER_CODE_ID.get(code, "tidak diketahui"),
            "temp_max_c": daily.get("temperature_2m_max", [None])[i],
            "temp_min_c": daily.get("temperature_2m_min", [None])[i],
            "rain_chance_pct": daily.get("precipitation_probability_max", [None])[i],
        })

    return {"location": label, "forecast": forecast}


def setup() -> None:
    registry.register(
        name="weather.get_forecast",
        description=(
            "Mengambil prakiraan cuaca untuk sebuah kota (suhu, kondisi langit, "
            "peluang hujan). Gunakan saat user bertanya tentang cuaca, suhu, "
            "atau kondisi langit di suatu tempat."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "city": {
                    "type": "string", "minLength": 1, "maxLength": 80,
                    "description": "Nama kota, contoh: Manado. Sertakan negara jika ambigu.",
                },
                "days": {
                    "type": "integer", "minimum": 1, "maximum": 7, "default": 1,
                    "description": "Jumlah hari prakiraan, 1 = hari ini saja",
                },
            },
            "required": ["city"],
        },
        handler=get_forecast,
        category="info_search",
    )
