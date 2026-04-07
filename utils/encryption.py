from __future__ import annotations

from pathlib import Path
from cryptography.fernet import Fernet


def load_or_create_key(key_path: Path) -> bytes:
    if key_path.exists():
        return key_path.read_bytes()
    key = Fernet.generate_key()
    key_path.write_bytes(key)
    key_path.chmod(0o600)
    return key


def encrypt_text(text: str, key: bytes) -> str:
    return Fernet(key).encrypt(text.encode()).decode()


def decrypt_text(ciphertext: str, key: bytes) -> str:
    return Fernet(key).decrypt(ciphertext.encode()).decode()
