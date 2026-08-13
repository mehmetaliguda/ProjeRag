"""
mssql_crypto.py
----------------
MSSQL baglanti parolasini DB'de duz metin olarak tutmamak icin
Fernet (simetrik) sifreleme/cozme yardimcisi.

Anahtar MSSQL_ENC_KEY ortam degiskeninden okunur (rag.env icine eklenmeli).
Yeni bir anahtar uretmek icin:

    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

Uretilen degeri rag.env dosyasina ekle:

    MSSQL_ENC_KEY=<uretilen_anahtar>

MSSQL_ENC_KEY tanimli degilse sifreleme/cozme calismaz ve acik bir
ValueError firlatilir (sessizce duz metin saklamaya DUSULMEZ).
"""

from cryptography.fernet import Fernet, InvalidToken

from dotenv_rag import require_env_variable


def _get_fernet() -> Fernet:
    key = require_env_variable("MSSQL_ENC_KEY")
    key_bytes = key.encode("utf-8") if isinstance(key, str) else key
    try:
        return Fernet(key_bytes)
    except (ValueError, TypeError) as e:
        raise ValueError(
            "MSSQL_ENC_KEY gecersiz bir Fernet anahtari degil. "
            "'python -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\"' ile yeni bir anahtar uret."
        ) from e


def encrypt_password(plain_password: str) -> str:
    """Duz metin parolayi sifreleyip base64 (str) olarak dondurur."""
    if not plain_password:
        raise ValueError("Sifrelenecek parola bos olamaz.")
    token = _get_fernet().encrypt(plain_password.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_password(encrypted_password: str) -> str:
    """Sifreli parolayi (str) coz, duz metin dondur."""
    if not encrypted_password:
        raise ValueError("Cozulecek sifreli parola bos olamaz.")
    try:
        return _get_fernet().decrypt(encrypted_password.encode("utf-8")).decode("utf-8")
    except InvalidToken as e:
        raise ValueError(
            "MSSQL parolasi cozulemedi (yanlis MSSQL_ENC_KEY veya bozuk veri)."
        ) from e
