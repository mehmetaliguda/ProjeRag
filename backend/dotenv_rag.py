"""
dotenv_rag.py
-------------
Proje genelinde kullanilan ortak .env yukleme ve okuma yardimcisi.
Varsayilan dosya adi "rag.env" (proje kokunde veya ust dizinlerde aranir).

Kullanim:
    from dotenv_rag import load_dotenv, get_env_variable, require_env_variable

    load_dotenv()
    model = get_env_variable("OLLAMA_MODEL", "qwen2.5:7b-instruct")
    key   = require_env_variable("SOME_REQUIRED_KEY")
"""

import os
from pathlib import Path
from dotenv import load_dotenv as _dotenv_load

_ENV_FILENAME = "rag.env"
_loaded = False


def _find_env_file(filename: str = _ENV_FILENAME, start: str | None = None) -> Path | None:
    """Verilen dosyayi calisma dizininden baslayip ust dizinlere dogru arar."""
    start_path = Path(start or os.getcwd()).resolve()
    for directory in [start_path, *start_path.parents]:
        candidate = directory / filename
        if candidate.exists():
            return candidate
    return None


def load_dotenv(env_path: str | None = None, override: bool = False) -> bool:
    """
    rag.env dosyasini yukler.
    env_path verilirse dogrudan o dosya kullanilir, verilmezse otomatik aranir.
    """
    global _loaded

    path = Path(env_path) if env_path else _find_env_file()

    if path is None or not path.exists():
        print(f"[dotenv_rag] UYARI: '{_ENV_FILENAME}' bulunamadi, sistem ortam degiskenleri kullanilacak.")
        _loaded = True
        return False

    _dotenv_load(dotenv_path=path, override=override)
    _loaded = True
    print(f"[dotenv_rag] Ortam degiskenleri yuklendi: {path}")
    return True


def get_env_variable(key: str, default: str | None = None) -> str | None:
    """Bir ortam degiskenini okur. Henuz load_dotenv() cagrilmadiysa otomatik cagirir."""
    if not _loaded:
        load_dotenv()
    return os.getenv(key, default)


def require_env_variable(key: str) -> str:
    """Zorunlu bir ortam degiskenini okur, yoksa ValueError firlatir."""
    value = get_env_variable(key)
    if not value:
        raise ValueError(
            f"'{key}' ortam degiskeni bulunamadi! "
            f"'{_ENV_FILENAME}' dosyasina eklediginden emin ol."
        )
    return value