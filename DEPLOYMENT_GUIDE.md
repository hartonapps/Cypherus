# Beginner Deployment Guide (Termux + Panels)

This guide is for absolute beginners.

## 1) What you need first

1. A Telegram account (your own user account).
2. Telegram API credentials from https://my.telegram.org:
   - `api_id`
   - `api_hash`
3. Android phone with Termux **or** a Linux VPS panel.

---

## 2) Option A: Run on Termux (Android)

### Step A1) Install Termux packages
```bash
pkg update -y && pkg upgrade -y
pkg install -y python git ffmpeg libjpeg-turbo
python -m pip install --upgrade pip wheel
# lightweight dependency set
```

### Step A2) Get the project
```bash
git clone <YOUR_REPO_URL> cypherus
cd cypherus
pip install -r requirements.txt
```

### Step A3) Add your Telegram account
```bash
python frontend.py
```
Pick `1) Create/Login account`, then enter:
- API ID
- API Hash
- phone number
- login code (and 2FA password if enabled)

### Step A4) Start userbot
```bash
python main.py
```
Now open Telegram → Saved Messages and run commands like:
- `.menu`
- `.ping`

### Step A5) Keep it alive after closing Termux
Use `tmux`:
```bash
pkg install -y tmux
tmux new -s cypherus
python main.py
```
Detach with `CTRL+B`, then `D`.
Re-open session:
```bash
tmux attach -t cypherus
```

---

## 3) Option B: Run on a hosting panel (Pterodactyl/Katabump-like)

Most panels are similar:

1. Create a new **Python** app/server.
2. Startup command:
   ```bash
   python main.py
   ```
3. Upload project files (or git clone in startup/install script).
4. Install dependencies during setup:
   ```bash
   pip install -r requirements.txt
   ```
5. Open console once and run:
   ```bash
   python frontend.py
   ```
   to create/login Telegram account session.
6. Restart server with `python main.py` as default command.

### Katabump note
If Katabump gives you terminal + persistent storage + Python runtime, the above steps are the same.
If it does **not** allow interactive login input, do the login once in Termux (`frontend.py`), then upload your `users/` folder to the panel.

---

## 4) First commands to test

In Saved Messages:
1. `.menu`
2. `.ping`
3. `.calc 5*8`
4. `.qr hello`
5. Reply to an image with `.s`

---

## 5) Common errors (easy fixes)

- `No user accounts found`:
  - run `python frontend.py` first.

- `ModuleNotFoundError`:
  - run `pip install -r requirements.txt`.

- Downloader fails:
  - update yt-dlp: `pip install -U yt-dlp`.

- Session issues:
  - use `.logout` or `.reset`, then login again via `frontend.py`.

---

## 6) Safety tips

- Never share `users/.master.key`.
- Never share files inside `users/*.json`.
- Use this only on your own account/chats and responsibly.
