# Cypherus Multi-User Telegram Userbot (Termux Friendly)

A **multi-user Telegram userbot platform** built with **Telethon** that supports:

- Per-user login with Telegram **API ID / API Hash**
- Encrypted multi-user string sessions
- CLI frontend account manager (`frontend.py`)
- Userbot commands with `.` prefix (`.help`, `.menu`, `.ping`, etc.)
- View-once/expiring media auto-save (best-effort based on TTL metadata)
- Free AI/utility/download tooling without paid APIs

> ⚠️ Important: Userbots can violate Telegram Terms in some contexts. Use responsibly and only on accounts/chats you control.

## Project Structure

- `frontend.py` – interactive account/session manager
- `main.py` – starts userbot clients and command handlers
- `config.py` – settings
- `users/` – encrypted user session data
- `utils/` – encryption, AI, media, downloader, command utilities
- `requirements.txt` – dependencies

## Termux Installation

```bash
pkg update -y && pkg upgrade -y
pkg install -y python ffmpeg libjpeg-turbo
python -m pip install --upgrade pip wheel
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

## Commands (run from your own account messages)

Use commands in **Saved Messages** or any chat where your account can send messages.

- `.menu` / `.help` – command guide
- `.ping` – latency check
- `.logout` – log out current account session
- `.reset` – clear current account session files
- `.autoreply on|off <text>` – set automatic reply
- `.autoreact on|off 😀🔥...` – auto reactions
- `.s` – reply to image/sticker, convert to sticker (webp)
- `.toimg` – reply to sticker, convert to PNG
- `.kang <pack_short_name> 😀` – add replied sticker/image to an existing sticker pack
- `.dl <url>` – download media (YouTube/TikTok/Instagram etc. via `yt-dlp`)
- `.meta <url>` – media metadata extraction
- `.gpt <text>` / `.ask <question>` – free AI reply (public endpoint fallback + local fallback)
- `.summarize <text>` – extractive summarization (local)
- `.translate <text> to <language>` – translation via libretranslate public endpoint with local fallback
- `.qr <text>` – generate QR code
- `.short <url>` – URL shortener via is.gd
- `.calc <expr>` – safe math evaluator
- `.tagall` – tag all members in group
- `.kick @user`, `.promote @user`, `.demote @user`
- `.pin` / `.unpin`
- `.antispam on|off`

## Notes on View-Once / Expiring Media

Telegram may restrict access to true one-time media in some scenarios. This bot performs a **best-effort extraction** by detecting TTL/self-destruct style metadata and auto-downloading media as soon as it arrives, then forwarding/saving to Saved Messages and/or local storage.

## Security

- Sessions are stored encrypted with `cryptography.Fernet`
- Master encryption key stored in `users/.master.key` (chmod 600 recommended)
- Per-user logout/reset controls included

