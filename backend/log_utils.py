# log_utils.py - Gunluk istek loglarini backend/log/YYYY-MM-DD.log dosyasina yazar
#
# Her gun icin tek bir dosya olusur (ornek: log/2026-08-17.log) ve o gun
# icindeki tum istekler (mesaj, saat, oda/dosya, IP) ayni dosyaya eklenir.

import os
import threading
from datetime import datetime

# Bu dosya backend/ altinda oldugu icin log klasoru otomatik olarak
# backend/log/ olur.
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "log")
os.makedirs(LOG_DIR, exist_ok=True)

# Ayni anda birden fazla istek gelirse dosyaya yazma sirasinda satirlarin
# birbirine karismamasi icin basit bir kilit kullaniyoruz.
_lock = threading.Lock()


def _get_log_path():
    today = datetime.now().strftime("%Y-%m-%d")
    return os.path.join(LOG_DIR, f"{today}.log")


def get_client_ip(request):
    """Flask 'request' nesnesinden gercek client IP'yi cikarir.
    Nginx/reverse proxy arkasindaysan X-Forwarded-For'u dikkate alir."""
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        # X-Forwarded-For birden fazla IP icerebilir (proxy zinciri),
        # ilk IP gercek client'tir.
        return forwarded_for.split(",")[0].strip()
    return request.remote_addr or "bilinmiyor"


def log_request(ip, message, rooms, notebook_id=None):
    """
    ip: istek yapan istemcinin IP adresi
    message: kullanicinin sordugu soru / istek mesaji (bos olabilir)
    rooms: istek yapilan oda(lar)/dosya(lar) - list, string veya None olabilir
    notebook_id: istegin ait oldugu notebook'un id'si (bos olabilir)
    """
    if not rooms:
        rooms_str = "-"
    elif isinstance(rooms, (list, tuple)):
        rooms_str = ", ".join(rooms) if rooms else "-"
    else:
        rooms_str = str(rooms)

    notebook_str = str(notebook_id) if notebook_id is not None else "-"
    message_str = (message or "-").replace("\n", " ").strip()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_line = (
        f"[{timestamp}] IP: {ip} | Oda(lar)/Dosya(lar): {rooms_str} | "
        f"Notebook: {notebook_str} | Mesaj: {message_str}\n\n"
    )

    with _lock:
        with open(_get_log_path(), "a", encoding="utf-8") as f:
            f.write(log_line)