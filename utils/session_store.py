from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from utils.encryption import decrypt_text, encrypt_text, load_or_create_key


class SessionStore:
    def __init__(self, users_dir: Path):
        self.users_dir = users_dir
        self.users_dir.mkdir(parents=True, exist_ok=True)
        self.key_path = self.users_dir / ".master.key"
        self.key = load_or_create_key(self.key_path)

    def _user_path(self, username: str) -> Path:
        return self.users_dir / f"{username}.json"

    def save_user(self, username: str, data: dict[str, Any]) -> None:
        out = dict(data)
        out["string_session"] = encrypt_text(data["string_session"], self.key)
        self._user_path(username).write_text(json.dumps(out, indent=2), encoding="utf-8")

    def load_user(self, username: str) -> dict[str, Any]:
        payload = json.loads(self._user_path(username).read_text(encoding="utf-8"))
        payload["string_session"] = decrypt_text(payload["string_session"], self.key)
        return payload

    def delete_user(self, username: str) -> None:
        p = self._user_path(username)
        if p.exists():
            p.unlink()

    def list_users(self) -> list[str]:
        return sorted([p.stem for p in self.users_dir.glob("*.json")])
