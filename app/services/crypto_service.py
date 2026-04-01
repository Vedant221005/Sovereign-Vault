import os
from pathlib import Path

from cryptography.fernet import Fernet


def _get_fernet() -> Fernet:
    key = os.getenv("FERNET_KEY")
    if not key:
        raise RuntimeError("FERNET_KEY is not configured")
    return Fernet(key.encode("utf-8"))


def encrypt_bytes(raw_data: bytes) -> bytes:
    return _get_fernet().encrypt(raw_data)


def decrypt_bytes(encrypted_data: bytes) -> bytes:
    return _get_fernet().decrypt(encrypted_data)


def get_storage_dir() -> Path:
    storage_path = os.getenv("ENCRYPTED_STORAGE_DIR", "storage/encrypted")
    path = Path(storage_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    path.mkdir(parents=True, exist_ok=True)
    return path
