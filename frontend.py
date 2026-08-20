from __future__ import annotations

import asyncio
import json
from getpass import getpass
from pathlib import Path

from telethon import TelegramClient
from telethon.sessions import StringSession

from config import USERS_DIR
from utils.session_store import SessionStore

ENV_PATH = Path(".env")


def load_local_env_file(path: Path = ENV_PATH) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.exists():
        return data
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            data[key] = value
    return data


def save_env_value(key: str, value: str | None, path: Path = ENV_PATH) -> None:
    lines: list[str] = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                lines.append(line)
                continue
            existing_key = stripped.split("=", 1)[0].strip()
            if existing_key != key:
                lines.append(line)
    elif value is not None and Path(".env.example").exists():
        lines = Path(".env.example").read_text(encoding="utf-8").splitlines()
    if value is not None:
        rendered = value.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'{key}="{rendered}"')
    path.write_text(("\n".join(lines).rstrip() + "\n") if lines else "", encoding="utf-8")


def configure_control_bot() -> None:
    current = load_local_env_file().get("CONTROL_BOT_TOKEN", "")
    print(f"Current CONTROL_BOT_TOKEN: {'set' if current else 'not set'}")
    token = input("Enter control bot token (leave blank to clear): ").strip()
    if token:
        save_env_value("CONTROL_BOT_TOKEN", token)
        print("Control bot token saved to .env")
    else:
        save_env_value("CONTROL_BOT_TOKEN", None)
        print("Control bot token removed from .env")


async def create_account(store: SessionStore) -> None:
    label = input("Choose local username label (e.g., mymain): ").strip()
    if not label:
        print("Label cannot be empty.")
        return
    api_id_raw = input("Telegram API ID: ").strip()
    if not api_id_raw.isdigit():
        print("API ID must be an integer.")
        return
    api_id = int(api_id_raw)
    api_hash = (getpass("Telegram API Hash: ") or "").strip()
    if not api_hash:
        print("API Hash cannot be empty.")
        return

    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        phone = (input("Phone number with country code (e.g., +123...): ") or "").strip()
        if not phone:
            print("Phone number cannot be empty.")
            await client.disconnect()
            return
        await client.send_code_request(phone)
        code = input("Enter login code: ").strip()
        try:
            await client.sign_in(phone=phone, code=code)
        except Exception:
            pwd = getpass("2FA password: ")
            await client.sign_in(password=pwd)

    me = await client.get_me()
    session = client.session.save()
    app_title = f"{me.first_name or ''} {me.last_name or ''}".strip() or me.username or str(me.id)

    store.save_user(
        label,
        {
            "label": label,
            "display_name": app_title,
            "api_id": api_id,
            "api_hash": api_hash,
            "user_id": me.id,
            "string_session": session,
            "active": True,
            "settings": {
                "autoreply": {"enabled": False, "text": "I'm currently busy."},
                "autoreact": {"enabled": False, "emojis": "🔥"},
                "antispam": {"enabled": False, "limit": 6, "window": 12},
            },
        },
    )

    await client.disconnect()
    print(f"✅ Account '{label}' saved for {app_title}")


def list_accounts(store: SessionStore) -> None:
    users = store.list_users()
    if not users:
        print("No accounts found.")
        return
    for i, user in enumerate(users, 1):
        data = store.load_user(user)
        print(f"{i}. {user} -> {data.get('display_name')} (active={data.get('active', True)})")


def toggle_active(store: SessionStore) -> None:
    label = input("Account label: ").strip()
    data = store.load_user(label)
    data["active"] = not data.get("active", True)
    store.save_user(label, data)
    print(f"{label} active => {data['active']}")


def remove_account(store: SessionStore) -> None:
    label = input("Account label to remove: ").strip()
    store.delete_user(label)
    print(f"Removed: {label}")


def export_accounts_json(store: SessionStore) -> None:
    export_path = USERS_DIR / "accounts_export.json"
    payload = {}
    for label in store.list_users():
        data = store.load_user(label)
        data["string_session"] = "***redacted***"
        payload[label] = data
    export_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Exported metadata to {export_path}")


def main() -> None:
    store = SessionStore(USERS_DIR)
    menu = (
        "\n=== Cypherus Frontend ===\n"
        "1) Create/Login account\n"
        "2) List accounts\n"
        "3) Enable/Disable account\n"
        "4) Remove account\n"
        "5) Export account metadata\n"
        "6) Configure control bot token\n"
        "0) Exit\n"
    )

    while True:
        print(menu)
        choice = input("Select: ").strip()
        if choice == "1":
            asyncio.run(create_account(store))
        elif choice == "2":
            list_accounts(store)
        elif choice == "3":
            toggle_active(store)
        elif choice == "4":
            remove_account(store)
        elif choice == "5":
            export_accounts_json(store)
        elif choice == "6":
            configure_control_bot()
        elif choice == "0":
            break
        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main()
