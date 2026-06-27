"""
core/netinfo.py

Helper kecil untuk mendeteksi alamat IP LAN server ini — dipakai dashboard
supaya user tahu URL apa yang harus dibuka dari device lain di jaringan
yang sama (laptop, HP lain, dst), tanpa harus cari manual lewat `ip addr` /
`ifconfig` / Settings Android.
"""

from __future__ import annotations

import socket


def detect_lan_ip() -> str | None:
    """Deteksi IP LAN keluar server ini.

    Trik: buka socket UDP dan "connect" ke alamat publik (8.8.8.8:80).
    UDP connect tidak benar-benar mengirim paket apa pun — ini hanya
    membuat OS memilih route/interface yang akan dipakai, lalu kita baca
    alamat lokal dari socket itu. Tidak butuh koneksi internet yang benar
    -benar aktif, tidak butuh dependency tambahan, dan jalan di Termux
    maupun desktop.

    Mengembalikan None kalau deteksi gagal (misal: tidak ada interface
    network aktif sama sekali).
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(0.5)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            if ip and ip != "0.0.0.0":
                return ip
    except OSError:
        pass
    return None
