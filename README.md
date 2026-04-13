# Cypherus Multi-User Telegram Userbot (Termux Friendly)

A **multi-user Telegram userbot platform** built with **Telethon** that supports:

- Per-user login with Telegram **API ID / API Hash**
- Encrypted multi-user string sessions
- CLI frontend account manager (`frontend.py`)
- Userbot commands with `.` prefix (`.help`, `.menu`, `.ping`, etc.)
- View-once/expiring media auto-save (best-effort based on TTL metadata)
- Free AI/utility/download tooling without paid APIs

> ⚠️ Important: Userbots can violate Telegram Terms in some contexts. Use responsibly and only on accounts/chats you control.

## Termux Installation

```bash
pkg update -y && pkg upgrade -y
pkg install -y python ffmpeg libjpeg-turbo
python -m pip install --upgrade pip wheel
# lightweight requirements (no cryptography/pillow)
pip install -r requirements.txt
```

## Run

1. Create/login accounts:

```bash
python frontend.py
```

2. Start all active userbot sessions:

```bash
python main.py
```

Use commands in **Saved Messages** or any chat where your account can send messages.
