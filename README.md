# Cypherus Userbot (Frontend-first)

Cypherus is a multi-user Telethon userbot focused on a simple local workflow:

- manage accounts with `frontend.py`
- run active accounts with `main.py`
- auto-join official channel/group on startup (if configured)

## Quick Start

```bash
python frontend.py
# create/login account and keep it active
python main.py
```

If no active accounts exist, `main.py` opens the frontend manager automatically.

## Environment

Create `.env` from `.env.example`:

```bash
cp .env.example .env
```

Important variables:

- `OFFICIAL_CHANNEL_USERNAME` (supports `name`, `@name`, or `https://t.me/name`)
- `OFFICIAL_GROUP_USERNAME` (supports `name`, `@name`, or `https://t.me/name`)
- `AI_HORDE_API_KEY` (optional, for better image generation quota)

## Core Commands

- `.menu` / `.help`
- `.ping`
- `.profile`
- `.mode public|private`
- `.restart`

### Media / AI

- `.generateimg <prompt>` (AI Horde image generation)
- reply voice/audio + `.transcribe` (free transcription endpoint)
- `.dl <url>`
- `.song <query>`
- `.search <query>` / `.ytsearch <query>`

### Group Utilities

- `.join <invite_or_username>`
- `.leave [target]`
- `.leavesilently [target]` (best-effort; Telegram may still show leave service message)

## Notes

- Startup logs now include official group/channel values and auto-join outcomes.
- On each startup, Cypherus sends a setup notice to your Saved Messages.
- Admin command system was removed from runtime.

## Requirements

See `requirements.txt` and install with:

```bash
pip install -r requirements.txt
```
