from __future__ import annotations

import asyncio
import json
from getpass import getpass

from telethon import TelegramClient
from telethon.sessions import StringSession

from config import USERS_DIR
from utils.session_store import SessionStore


async def create_account(store: SessionStore) -> None:
    label = input("Choose local username label (e.g., mymain): ").strip()
    api_id = int(input("Telegram API ID: ").strip())
    api_hash = getpass("Telegram API Hash: ").strip()

    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        phone = input("Phone number with country code (e.g., +123...): ").strip()
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
        elif choice == "0":
            break
        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main()
