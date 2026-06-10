import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings

PREFIX = "enc:"


def _fernet() -> Fernet:
    settings = get_settings()
    seed = (settings.financial_data_key or settings.jwt_secret).encode("utf-8")
    key = base64.urlsafe_b64encode(hashlib.sha256(seed).digest())
    return Fernet(key)


def encrypt_financial_text(value: str) -> str:
    if not value or value.startswith(PREFIX):
        return value
    return f"{PREFIX}{_fernet().encrypt(value.encode('utf-8')).decode('utf-8')}"


def decrypt_financial_text(value: str) -> str:
    if not value or not value.startswith(PREFIX):
        return value
    try:
        return _fernet().decrypt(value[len(PREFIX) :].encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return value
