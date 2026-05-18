from __future__ import annotations

import base64
import hashlib
import os
from pathlib import Path


def load_or_create_key(key_path: Path) -> bytes:
    if key_path.exists():
        return key_path.read_bytes()
    key = base64.urlsafe_b64encode(os.urandom(32))
    key_path.write_bytes(key)
    key_path.chmod(0o600)
    return key


def _keystream(key: bytes, length: int) -> bytes:
    out = bytearray()
    counter = 0
    while len(out) < length:
        block = hashlib.sha256(key + counter.to_bytes(4, "big")).digest()
        out.extend(block)
        counter += 1
    return bytes(out[:length])


def encrypt_text(text: str, key: bytes) -> str:
    raw = text.encode("utf-8")
    ks = _keystream(key, len(raw))
    cipher = bytes([a ^ b for a, b in zip(raw, ks)])
    return base64.urlsafe_b64encode(cipher).decode("utf-8")


def decrypt_text(ciphertext: str, key: bytes) -> str:
    enc = base64.urlsafe_b64decode(ciphertext.encode("utf-8"))
    ks = _keystream(key, len(enc))
    raw = bytes([a ^ b for a, b in zip(enc, ks)])
    return raw.decode("utf-8")
