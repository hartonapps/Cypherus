from __future__ import annotations

import asyncio
import json
import random
import re
import shutil
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from pathlib import Path

import httpx
from telethon import TelegramClient, events, functions, types
from telethon.sessions import StringSession

from config import (
    COMMAND_PREFIX,
    DEFAULT_ANTISPAM_LIMIT,
    DEFAULT_ANTISPAM_WINDOW,
    LOG_DIR,
    MEDIA_DIR,
    SAVE_EXTRACTED_TO_LOCAL,
    SAVE_EXTRACTED_TO_SAVED_MESSAGES,
    USERS_DIR,
)
from utils.ai_tools import ask_free_ai, summarize_text, translate_text
from utils.downloaders import download_media, extract_metadata
from utils.helpers import build_qr_png_bytes, safe_calc, shorten_url
from utils.logger import setup_logger
from utils.media_tools import image_to_sticker, sticker_to_image
from utils.session_store import SessionStore

logger = setup_logger(LOG_DIR)
store = SessionStore(USERS_DIR)

HELP_TEXT = """**🚀 Cypherus Userbot Menu**

**Core**
• `.menu` / `.help` → show this menu
• `.ping` → check userbot response speed
• `.logout` → set this account inactive
• `.reset` → delete local profile/session file

**Automation**
• `.away <text>` / `.away off` → AFK auto-reply
• `.schedule <10m|HH:MM> <message>` → send later
• `.filter <word> <response>` → keyword auto-reply

**Privacy / Logs**
• `.ghostmode on|off`
• `.anti-delete on|off`
• `.anti-edit on|off`
• `.hideonline on|off`

**Media**
• `.vvwatch on|off` → monitor expiring/view-once
• Reply media + `.vvsave` → force-save to Saved Messages
• Reply media + `.compress`
• Reply media + `.rename <newname>`
• Reply media + `.tomp4`
• Reply image + `.ocr`
• Reply image + `.s` | Reply sticker + `.toimg`

**Downloads**
• `.dl <url>`
• `.playlist <url>`
• `.song <query>`
• `.meta <url>`

**AI / Tools**
• `.gpt <text>` / `.ask <text>`
• `.summarize <text>`
• `.translate <text> to <lang>`
• `.qr <text>`
• `.short <url>`
• `.calc <expression>`

**Group Admin**
• `.tagall`
• `.kick @user` `.promote @user` `.demote @user`
• `.warn @user` `.mute @user 10m`
• `.join <invite_link>`
• `.pin` / `.unpin`

**Smart / Viral / Utility+**
• `.persona calm|savage|default`
• `.roast @user` `.ship @u1 @u2` `.rate @user` `.vibecheck` `.truth` `.dare`
• `.lockchat on|off` `.blockword <word>` `.stats` `.activity @user` `.usage`
• `.joke` `.quote` `.facts` `.backup` `.restore`
• `.save <name>` (reply) `.get <name>` `.list`
• `.daily` `.rank`
"""



COMMAND_HELP = {
    "menu": "Usage: .menu\nShow full command menu.",
    "ping": "Usage: .ping\nCheck response speed.",
    "away": "Usage: .away <text> | .away off\nEnable/disable AFK auto-reply.",
    "schedule": "Usage: .schedule <10m|HH:MM> <message>\nSend a message later.",
    "filter": "Usage: .filter <word> <response>\nAuto-reply when keyword is detected.",
    "vvwatch": "Usage: .vvwatch on|off\nAuto-monitor expiring/view-once media.",
    "vvsave": "Usage: reply media + .vvsave\nForce save replied media to Saved Messages.",
    "anti-delete": "Usage: .anti-delete on|off\nRecover deleted message text from cache.",
    "anti-edit": "Usage: .anti-edit on|off\nLog old/new message text on edits.",
    "lockchat": "Usage: .lockchat on|off\nBlock private incoming chats with lock reply.",
    "blockword": "Usage: .blockword <word>\nDelete messages containing that word.",
    "persona": "Usage: .persona default|calm|savage\nSwitch AI personality mode.",
    "gpt": "Usage: .gpt <text>\nAsk AI with current persona + memory.",
    "ask": "Usage: .ask <text>\nAlias of .gpt.",
    "summarize": "Usage: .summarize <text> or reply + .summarize\nSummarize text.",
    "translate": "Usage: .translate <text> to <lang>\nTranslate text.",
    "dl": "Usage: .dl <url>\nDownload media from URL.",
    "playlist": "Usage: .playlist <url>\nDownload playlist.",
    "song": "Usage: .song <query>\nSearch and download first song result.",
    "meta": "Usage: .meta <url>\nShow metadata.",
    "compress": "Usage: reply media + .compress\nCompress and resend media.",
    "rename": "Usage: reply media + .rename <newname>\nRename and resend media.",
    "tomp4": "Usage: reply video/gif + .tomp4\nConvert media to MP4.",
    "ocr": "Usage: reply image + .ocr\nExtract text from image.",
    "save": "Usage: reply message + .save <name>\nSave message reference by key.",
    "get": "Usage: .get <name>\nRecall saved message by key.",
    "list": "Usage: .list\nList saved keys.",
    "stats": "Usage: .stats\nShow usage counters + active chats.",
    "usage": "Usage: .usage\nQuick usage summary.",
    "daily": "Usage: .daily\nClaim daily XP.",
    "rank": "Usage: .rank\nShow XP + level.",
    "roast": "Usage: .roast @user\nSend fun roast.",
    "ship": "Usage: .ship @u1 @u2\nGenerate compatibility score.",
    "rate": "Usage: .rate @user\nRate user 1-10.",
    "vibecheck": "Usage: .vibecheck\nRandom vibe result.",
    "truth": "Usage: .truth\nTruth prompt.",
    "dare": "Usage: .dare\nDare prompt.",
    "backup": "Usage: .backup\nCreate local profile backup.",
    "restore": "Usage: .restore\nRestore local profile backup.",
}


def resolve_help(query: str) -> str:
    q = query.strip().lower().lstrip('.')
    if not q:
        return HELP_TEXT + "\n\nTip: .help <command>  (example: .help vvwatch)"
    if q in COMMAND_HELP:
        return f"**.{q}**\n{COMMAND_HELP[q]}"
    matches = [k for k in COMMAND_HELP if q in k]
    if matches:
        short = "\n".join([f"• .{m}" for m in matches[:10]])
        return f"Command not exact. Did you mean:\n{short}"
    return "Command not found. Use .menu"


def parse_command(text: str) -> tuple[str, str]:
    raw = text[len(COMMAND_PREFIX) :].strip()
    if not raw:
        return "", ""
    parts = raw.split(maxsplit=1)
    return parts[0].lower(), (parts[1] if len(parts) > 1 else "")


def parse_duration(text: str) -> int:
    m = re.fullmatch(r"(\d+)([smhd])", text.strip().lower())
    if not m:
        raise ValueError("Use duration like 10s, 5m, 2h, 1d")
    val, unit = int(m.group(1)), m.group(2)
    mult = {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]
    return val * mult


def parse_schedule_time(text: str) -> int:
    text = text.strip().lower()
    if re.fullmatch(r"\d+[smhd]", text):
        return parse_duration(text)
    if re.fullmatch(r"\d{2}:\d{2}", text):
        hh, mm = map(int, text.split(":"))
        now = datetime.now()
        target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        return int((target - now).total_seconds())
    raise ValueError("Use 10m or HH:MM")


def is_expiring_or_viewonce(message) -> bool:
    if getattr(message, "ttl_period", None):
        return True
    media = getattr(message, "media", None)
    if not media:
        return False
    if getattr(media, "ttl_seconds", None):
        return True
    return False


async def save_message_to_saved(client: TelegramClient, text: str | None = None, file_path: Path | str | None = None):
    try:
        if file_path:
            await client.send_file("me", file_path, caption=text or "")
        elif text:
            await client.send_message("me", text)
    except Exception:
        pass


async def save_media_if_needed(client: TelegramClient, message, label: str, force: bool = False) -> Path | None:
    if not message.media:
        return None
    if not force and not is_expiring_or_viewonce(message):
        return None

    user_media_dir = MEDIA_DIR / label / "extracted"
    user_media_dir.mkdir(parents=True, exist_ok=True)
    try:
        local_path = await message.download_media(file=user_media_dir)
        if SAVE_EXTRACTED_TO_SAVED_MESSAGES:
            await save_message_to_saved(client, "[VV/EXP extracted]", local_path)
        logger.info("[extract] %s %s", label, local_path)
        return Path(local_path) if local_path else None
    except Exception as exc:
        logger.exception("[extract-error] %s :: %s", label, exc)
        return None


async def update_user_settings(label: str, mutator):
    data = store.load_user(label)
    mutator(data)
    store.save_user(label, data)


def ensure_settings(data: dict):
    s = data.setdefault("settings", {})
    s.setdefault("autoreply", {"enabled": False, "text": "I'm currently busy."})
    s.setdefault("autoreact", {"enabled": False, "emojis": "🔥"})
    s.setdefault("antispam", {"enabled": False, "limit": 6, "window": 12})
    s.setdefault("away", {"enabled": False, "text": "I'm busy, I'll reply later."})
    s.setdefault("filters", {})
    s.setdefault("ghostmode", False)
    s.setdefault("anti_delete", False)
    s.setdefault("anti_edit", False)
    s.setdefault("hideonline", False)
    s.setdefault("vvwatch", True)
    s.setdefault("warns", {})
    s.setdefault("persona", "default")
    s.setdefault("smart_ai", True)
    s.setdefault("chat_memory", {})
    s.setdefault("lockchat", False)
    s.setdefault("blockwords", [])
    s.setdefault("stats", {"messages_seen": 0, "messages_sent": 0, "commands": 0, "chat_hits": {}})
    s.setdefault("saved_items", {})
    s.setdefault("xp", {"points": 0, "daily_last": ""})


async def run_scheduled_send(client: TelegramClient, chat_id: int, delay: int, text: str):
    await asyncio.sleep(max(delay, 1))
    await client.send_message(chat_id, text)




async def fetch_fun_text(kind: str) -> str:
    endpoints = {
        "joke": "https://official-joke-api.appspot.com/random_joke",
        "quote": "https://api.quotable.io/random",
        "facts": "https://uselessfacts.jsph.pl/api/v2/facts/random",
    }
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.get(endpoints[kind])
            if r.is_success:
                d = r.json()
                if kind == "joke":
                    return f"{d.get('setup','')}\n{d.get('punchline','')}"
                if kind == "quote":
                    return f"{d.get('content','')} — {d.get('author','')}"
                return d.get('text') or d.get('fact') or 'No fact'
    except Exception:
        pass
    return f"{kind} endpoint unavailable"


def add_xp(data: dict, amount: int = 1):
    ensure_settings(data)
    data["settings"]["xp"]["points"] = int(data["settings"]["xp"].get("points", 0)) + amount

async def register_handlers(client: TelegramClient, label: str):
    anti_spam_map: dict[int, deque[float]] = defaultdict(deque)
    msg_cache: dict[tuple[int, int], dict] = {}

    @client.on(events.NewMessage(incoming=True))
    async def incoming_handler(event):
        msg = event.message
        data = store.load_user(label)
        ensure_settings(data)
        settings = data["settings"]
        settings["stats"]["messages_seen"] = int(settings["stats"].get("messages_seen", 0)) + 1
        chat_hits = settings["stats"].setdefault("chat_hits", {})
        chat_hits[str(event.chat_id)] = int(chat_hits.get(str(event.chat_id), 0)) + 1

        msg_cache[(event.chat_id, msg.id)] = {
            "text": msg.raw_text or "",
            "from": event.sender_id,
            "has_media": bool(msg.media),
            "date": str(msg.date),
        }

        if settings.get("vvwatch", True):
            await save_media_if_needed(client, msg, label)

        if settings.get("lockchat", False) and event.is_private and not event.out:
            await event.reply("🔒 Chat locked right now.")
            return

        blockwords = [w.lower() for w in settings.get("blockwords", [])]
        if any(w in (msg.raw_text or "").lower() for w in blockwords):
            await event.delete()
            return

        if settings.get("away", {}).get("enabled") and event.is_private and not event.out:
            await event.reply(settings["away"].get("text") or "I'm busy, I'll reply later.")

        for k, v in settings.get("filters", {}).items():
            if k.lower() in (msg.raw_text or "").lower() and not event.out:
                await event.reply(v)
                break

        autoreply = settings.get("autoreply", {})
        if autoreply.get("enabled") and event.is_private and not event.out:
            await event.reply(autoreply.get("text", "I'm currently away."))

        if settings.get("autoreact", {}).get("enabled"):
            em = settings["autoreact"].get("emojis", "🔥")[0]
            try:
                await client(functions.messages.SendReactionRequest(
                    peer=event.chat_id,
                    msg_id=msg.id,
                    reaction=[types.ReactionEmoji(emoticon=em)],
                    big=False,
                    add_to_recent=True,
                ))
            except Exception:
                pass

        if settings.get("smart_ai", True) and event.is_private and not event.out and msg.raw_text:
            text = msg.raw_text.strip()
            if "?" in text or text.lower().startswith(("how", "why", "what", "who", "when", "can ")):
                mem = settings.setdefault("chat_memory", {}).setdefault(str(event.sender_id), [])
                mem.append(f"User: {text}")
                reply = await ask_free_ai(text, settings.get("persona", "default"), mem)
                mem.append(f"Bot: {reply}")
                settings["chat_memory"][str(event.sender_id)] = mem[-8:]
                await event.reply(reply[:1000])

        antispam = settings.get("antispam", {})
        if antispam.get("enabled") and event.is_group:
            uid, now = event.sender_id, time.time()
            dq = anti_spam_map[uid]
            dq.append(now)
            while dq and now - dq[0] > antispam.get("window", DEFAULT_ANTISPAM_WINDOW):
                dq.popleft()
            if len(dq) > antispam.get("limit", DEFAULT_ANTISPAM_LIMIT):
                try:
                    await event.delete()
                except Exception:
                    pass

        store.save_user(label, data)

    @client.on(events.MessageDeleted())
    async def on_deleted(event):
        data = store.load_user(label)
        ensure_settings(data)
        if not data["settings"].get("anti_delete", False):
            return
        for msg_id in event.deleted_ids:
            key = (event.chat_id, msg_id)
            cached = msg_cache.get(key)
            if cached:
                txt = f"🧹 Deleted message\nchat:{event.chat_id}\nfrom:{cached['from']}\ntext:{cached['text']}"
                await save_message_to_saved(client, txt)

    @client.on(events.MessageEdited(incoming=True))
    async def on_edited(event):
        data = store.load_user(label)
        ensure_settings(data)
        if not data["settings"].get("anti_edit", False):
            return
        key = (event.chat_id, event.message.id)
        old = msg_cache.get(key)
        if old and old.get("text") != (event.raw_text or ""):
            txt = (
                f"✏️ Edited message\nchat:{event.chat_id}\nfrom:{event.sender_id}\n"
                f"old:{old.get('text')}\nnew:{event.raw_text or ''}"
            )
            await save_message_to_saved(client, txt)
        msg_cache[key] = {
            "text": event.raw_text or "",
            "from": event.sender_id,
            "has_media": bool(event.message.media),
            "date": str(event.message.date),
        }

    @client.on(events.Raw(types.UpdateMessageReactions))
    async def reaction_save_handler(update):
        # Best effort: if you react with 👀 to a message, try extracting replied media.
        try:
            peer = update.peer
            msg_id = update.msg_id
            if not getattr(update, "reactions", None):
                return
            if "👀" not in str(update.reactions):
                return
            entity = await client.get_entity(peer)
            msg = await client.get_messages(entity, ids=msg_id)
            await save_media_if_needed(client, msg, label, force=True)
        except Exception:
            pass

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\."))
    async def command_handler(event):
        cmd, arg = parse_command(event.raw_text)
        if not cmd:
            return
        try:
            data = store.load_user(label)
            ensure_settings(data)
            data["settings"]["stats"]["commands"] = int(data["settings"]["stats"].get("commands", 0)) + 1
            data["settings"]["stats"]["messages_sent"] = int(data["settings"]["stats"].get("messages_sent", 0)) + 1
            store.save_user(label, data)

            if cmd in {"help", "menu"}:
                await event.edit(resolve_help(arg if cmd == "help" else ""))
            elif cmd == "ping":
                t0 = time.perf_counter()
                msg = await event.respond("🏓 Pong...")
                ms = (time.perf_counter() - t0) * 1000
                await msg.edit(f"🏓 Pong: {ms:.2f} ms")
                await event.delete()

            elif cmd == "away":
                if arg.strip().lower() == "off":
                    def m(d):
                        ensure_settings(d)
                        d["settings"]["away"] = {"enabled": False, "text": ""}
                    await update_user_settings(label, m)
                    await event.edit("AFK disabled.")
                elif arg.strip():
                    def m(d):
                        ensure_settings(d)
                        d["settings"]["away"] = {"enabled": True, "text": arg.strip()}
                    await update_user_settings(label, m)
                    await event.edit("AFK enabled.")
                else:
                    await event.edit("Usage: .away <text> OR .away off")

            elif cmd == "persona":
                mode = arg.strip().lower()
                if mode not in {"default", "calm", "savage"}:
                    await event.edit("Usage: .persona default|calm|savage")
                else:
                    def m(d):
                        ensure_settings(d)
                        d["settings"]["persona"] = mode
                    await update_user_settings(label, m)
                    await event.edit(f"Persona set: {mode}")

            elif cmd == "roast":
                target = arg.strip() or "you"
                roasts = ["{t} is running on 1% brain battery.", "{t} types like buffering internet.", "{t} got defeated by a captcha."]
                await event.edit(random.choice(roasts).format(t=target))

            elif cmd == "ship":
                p2 = arg.split()
                if len(p2) < 2:
                    await event.edit("Usage: .ship @user1 @user2")
                else:
                    pct = random.randint(40, 100)
                    await event.edit(f"💘 {p2[0]} + {p2[1]} = {pct}%")

            elif cmd == "rate":
                who = arg.strip() or "you"
                await event.edit(f"⭐ {who} is {random.randint(1,10)}/10")

            elif cmd == "vibecheck":
                await event.edit(random.choice(["✅ Passed vibe check", "⚠️ Suspicious vibes", "🔥 Elite vibes"]))

            elif cmd == "truth":
                await event.edit(random.choice(["What is your biggest fear?", "What secret are you hiding?", "Who do you miss most?"]))

            elif cmd == "dare":
                await event.edit(random.choice(["Send your last screenshot.", "Text 'I miss you' to your crush.", "Stay silent for 10 mins."]))

            elif cmd == "lockchat":
                st = arg.strip().lower()
                if st not in {"on", "off"}:
                    await event.edit("Usage: .lockchat on|off")
                else:
                    def m(d):
                        ensure_settings(d)
                        d["settings"]["lockchat"] = st == "on"
                    await update_user_settings(label, m)
                    await event.edit(f"lockchat {st}")

            elif cmd == "blockword":
                word = arg.strip().lower()
                if not word:
                    await event.edit("Usage: .blockword <word>")
                else:
                    def m(d):
                        ensure_settings(d)
                        arr = d["settings"].setdefault("blockwords", [])
                        if word not in arr:
                            arr.append(word)
                    await update_user_settings(label, m)
                    await event.edit(f"Blocked word: {word}")

            elif cmd == "stats":
                d = store.load_user(label); ensure_settings(d)
                st = d["settings"]["stats"]
                top = sorted(st.get("chat_hits", {}).items(), key=lambda x: int(x[1]), reverse=True)[:5]
                tops = "\n".join([f"{k}: {v}" for k,v in top]) or "none"
                await event.edit(f"seen={st.get('messages_seen',0)}\nsent={st.get('messages_sent',0)}\ncommands={st.get('commands',0)}\nTop chats:\n{tops}")

            elif cmd == "activity":
                if not arg.strip():
                    await event.edit("Usage: .activity @user")
                else:
                    await event.edit("Activity tracking per-user detail is limited; use .stats for active chats.")

            elif cmd == "usage":
                d = store.load_user(label); ensure_settings(d)
                st = d["settings"]["stats"]
                await event.edit(f"Usage:\ncommands={st.get('commands',0)}\nmessages_seen={st.get('messages_seen',0)}")

            elif cmd in {"joke", "quote", "facts"}:
                await event.edit(await fetch_fun_text(cmd))

            elif cmd == "backup":
                src = USERS_DIR / f"{label}.json"
                dst = USERS_DIR / f"{label}.backup.json"
                if src.exists():
                    dst.write_bytes(src.read_bytes())
                    await event.edit(f"Backup saved: {dst.name}")
                else:
                    await event.edit("No profile found")

            elif cmd == "restore":
                src = USERS_DIR / f"{label}.backup.json"
                dst = USERS_DIR / f"{label}.json"
                if src.exists():
                    dst.write_bytes(src.read_bytes())
                    await event.edit("Backup restored.")
                else:
                    await event.edit("No backup file.")

            elif cmd == "save":
                reply = await event.get_reply_message()
                name = arg.strip().lower()
                if not reply or not name:
                    await event.edit("Usage: reply + .save <name>")
                else:
                    def m(d):
                        ensure_settings(d)
                        d["settings"].setdefault("saved_items", {})[name] = {"chat": event.chat_id, "msg_id": reply.id}
                    await update_user_settings(label, m)
                    await event.edit(f"Saved key: {name}")

            elif cmd == "get":
                name = arg.strip().lower()
                d = store.load_user(label); ensure_settings(d)
                item = d["settings"].get("saved_items", {}).get(name)
                if not item:
                    await event.edit("Not found")
                else:
                    await client.forward_messages(event.chat_id, item["msg_id"], from_peer=item["chat"])
                    await event.delete()

            elif cmd == "list":
                d = store.load_user(label); ensure_settings(d)
                keys = list(d["settings"].get("saved_items", {}).keys())
                await event.edit("Saved keys:\n" + ("\n".join(keys) if keys else "none"))

            elif cmd == "daily":
                d = store.load_user(label); ensure_settings(d)
                today = datetime.utcnow().strftime("%Y-%m-%d")
                xp = d["settings"]["xp"]
                if xp.get("daily_last") == today:
                    await event.edit("Daily already claimed.")
                else:
                    xp["daily_last"] = today
                    xp["points"] = int(xp.get("points", 0)) + 25
                    store.save_user(label, d)
                    await event.edit("+25 XP daily claimed.")

            elif cmd == "rank":
                d = store.load_user(label); ensure_settings(d)
                points = int(d["settings"]["xp"].get("points", 0))
                level = points // 100 + 1
                await event.edit(f"XP: {points}\nLevel: {level}")

            elif cmd == "schedule":
                p = arg.split(maxsplit=1)
                if len(p) < 2:
                    await event.edit("Usage: .schedule <10m|HH:MM> <message>")
                else:
                    delay = parse_schedule_time(p[0])
                    asyncio.create_task(run_scheduled_send(client, event.chat_id, delay, p[1]))
                    await event.edit(f"Scheduled in {delay}s")

            elif cmd == "filter":
                p = arg.split(maxsplit=1)
                if len(p) < 2:
                    await event.edit("Usage: .filter <word> <response>")
                else:
                    word, response = p[0].lower(), p[1]
                    def m(d):
                        ensure_settings(d)
                        d["settings"].setdefault("filters", {})[word] = response
                    await update_user_settings(label, m)
                    await event.edit(f"Filter set for: {word}")

            elif cmd in {"ghostmode", "anti-delete", "anti-edit", "hideonline", "vvwatch", "antispam"}:
                state = arg.strip().lower()
                if state not in {"on", "off"}:
                    await event.edit(f"Usage: .{cmd} on|off")
                    return
                key = cmd.replace("-", "_")
                def m(d):
                    ensure_settings(d)
                    if key == "antispam":
                        d["settings"]["antispam"]["enabled"] = state == "on"
                    else:
                        d["settings"][key] = state == "on"
                await update_user_settings(label, m)
                await event.edit(f"{cmd} {state}")

            elif cmd == "vvsave":
                reply = await event.get_reply_message()
                if not reply or not reply.media:
                    await event.edit("Reply to media with .vvsave")
                else:
                    p = await save_media_if_needed(client, reply, label, force=True)
                    await event.edit(f"Saved: {p.name if p else 'failed'}")

            elif cmd == "compress":
                reply = await event.get_reply_message()
                if not reply or not reply.media:
                    await event.edit("Reply to image/video with .compress")
                    return
                tmp = MEDIA_DIR / label / "tmp"
                tmp.mkdir(parents=True, exist_ok=True)
                src = Path(await reply.download_media(file=tmp / "compress_src"))
                out = tmp / f"compressed_{src.stem}.mp4"
                import subprocess
                await asyncio.to_thread(subprocess.run, ["ffmpeg", "-y", "-i", str(src), "-vcodec", "libx264", "-crf", "30", str(out)], check=True)
                await client.send_file(event.chat_id, out, caption="Compressed")
                await event.delete()

            elif cmd == "rename":
                reply = await event.get_reply_message()
                if not reply or not reply.media or not arg.strip():
                    await event.edit("Usage: reply media + .rename <newname>")
                    return
                tmp = MEDIA_DIR / label / "tmp"
                tmp.mkdir(parents=True, exist_ok=True)
                src = Path(await reply.download_media(file=tmp / "rename_src"))
                dst = src.with_name(arg.strip())
                src.rename(dst)
                await client.send_file(event.chat_id, dst)
                await event.delete()

            elif cmd == "tomp4":
                reply = await event.get_reply_message()
                if not reply or not reply.media:
                    await event.edit("Reply to video/gif with .tomp4")
                    return
                tmp = MEDIA_DIR / label / "tmp"
                tmp.mkdir(parents=True, exist_ok=True)
                src = Path(await reply.download_media(file=tmp / "vid_src"))
                out = tmp / f"{src.stem}.mp4"
                import subprocess
                await asyncio.to_thread(subprocess.run, ["ffmpeg", "-y", "-i", str(src), str(out)], check=True)
                await client.send_file(event.chat_id, out)
                await event.delete()

            elif cmd == "ocr":
                reply = await event.get_reply_message()
                if not reply or not reply.media:
                    await event.edit("Reply to image with .ocr")
                    return
                tmp = MEDIA_DIR / label / "tmp"
                tmp.mkdir(parents=True, exist_ok=True)
                src = Path(await reply.download_media(file=tmp / "ocr_src"))
                async with httpx.AsyncClient(timeout=40) as x:
                    files = {"file": (src.name, src.read_bytes())}
                    data = {"apikey": "helloworld", "language": "eng"}
                    res = await x.post("https://api.ocr.space/parse/image", data=data, files=files)
                    txt = res.json().get("ParsedResults", [{}])[0].get("ParsedText", "No text")
                await event.edit(txt[:3900] or "No text found")

            elif cmd == "playlist":
                if not arg:
                    await event.edit("Usage: .playlist <url>")
                    return
                await event.edit("Downloading playlist audio/video...")
                import yt_dlp
                outdir = MEDIA_DIR / label / "playlist"
                outdir.mkdir(parents=True, exist_ok=True)
                def _dl():
                    with yt_dlp.YoutubeDL({"outtmpl": str(outdir / "%(playlist_index)s_%(title).70s.%(ext)s")}) as y:
                        y.download([arg])
                await asyncio.to_thread(_dl)
                await event.edit("Playlist download completed.")

            elif cmd == "storydl":
                await event.edit("Use .dl with direct story URL (Telegram/Instagram). @username story scraping is not reliable without platform auth.")

            elif cmd == "song":
                if not arg:
                    await event.edit("Usage: .song <name>")
                    return
                import yt_dlp
                outdir = MEDIA_DIR / label / "songs"
                outdir.mkdir(parents=True, exist_ok=True)
                await event.edit("Searching and downloading song...")
                def _song():
                    with yt_dlp.YoutubeDL({"format": "bestaudio", "outtmpl": str(outdir / "%(title).70s.%(ext)s")}) as y:
                        y.download([f"ytsearch1:{arg}"])
                await asyncio.to_thread(_song)
                latest = max(outdir.glob("*"), key=lambda p: p.stat().st_mtime)
                await client.send_file(event.chat_id, latest)
                await event.delete()

            elif cmd == "warn":
                if not event.is_group:
                    await event.edit("Group only")
                    return
                target = arg.strip()
                if not target and event.is_reply:
                    target = (await event.get_reply_message()).sender_id
                if not target:
                    await event.edit("Usage: .warn @user")
                    return
                ent = await client.get_entity(target)
                def m(d):
                    ensure_settings(d)
                    w = d["settings"].setdefault("warns", {})
                    uid = str(ent.id)
                    w[uid] = int(w.get(uid, 0)) + 1
                await update_user_settings(label, m)
                data = store.load_user(label)
                count = int(data["settings"].get("warns", {}).get(str(ent.id), 1))
                if count >= 3:
                    await client.kick_participant(event.chat_id, ent)
                    await event.edit(f"{ent.first_name} kicked (3 warns).")
                else:
                    await event.edit(f"Warned {ent.first_name}: {count}/3")

            elif cmd == "mute":
                if not event.is_group:
                    await event.edit("Group only")
                    return
                p = arg.split(maxsplit=1)
                if len(p) < 2:
                    await event.edit("Usage: .mute @user 10m")
                    return
                ent = await client.get_entity(p[0])
                seconds = parse_duration(p[1])
                until = datetime.utcnow() + timedelta(seconds=seconds)
                await client.edit_permissions(event.chat_id, ent, send_messages=False, until_date=until)
                await event.edit(f"Muted for {seconds}s")

            elif cmd == "join":
                if not arg:
                    await event.edit("Usage: .join <invite_link>")
                    return
                await client(functions.messages.ImportChatInviteRequest(hash=arg.split("/")[-1].replace("+", "")))
                await event.edit("Joined.")

            elif cmd in {"gpt", "ask"}:
                if not arg:
                    await event.edit(f"Usage: .{cmd} <text>")
                else:
                    d = store.load_user(label); ensure_settings(d)
                    mem = d["settings"].setdefault("chat_memory", {}).setdefault(str(event.chat_id), [])
                    mem.append(f"User: {arg}")
                    out = await ask_free_ai(arg, d["settings"].get("persona", "default"), mem)
                    mem.append(f"Bot: {out}")
                    d["settings"]["chat_memory"][str(event.chat_id)] = mem[-8:]
                    store.save_user(label, d)
                    await event.edit(out[:3900])

            elif cmd == "summarize":
                text = arg or ((await event.get_reply_message()).raw_text if event.is_reply else "")
                await event.edit(summarize_text(text) if text else "Usage: .summarize <text>")

            elif cmd == "translate":
                m = re.match(r"(.+)\s+to\s+([a-zA-Z-]+)$", arg)
                if not m:
                    await event.edit("Usage: .translate <text> to <lang>")
                else:
                    await event.edit(await translate_text(m.group(1), m.group(2)))

            elif cmd == "calc":
                await event.edit(f"Result: `{safe_calc(arg)}`" if arg else "Usage: .calc <expr>")
            elif cmd == "short":
                await event.edit(await shorten_url(arg) if arg else "Usage: .short <url>")
            elif cmd == "qr":
                if not arg:
                    await event.edit("Usage: .qr <text>")
                else:
                    await client.send_file(event.chat_id, await build_qr_png_bytes(arg), caption="QR")
                    await event.delete()
            elif cmd == "dl":
                if not arg:
                    await event.edit("Usage: .dl <url>")
                else:
                    await event.edit("Downloading...")
                    path = await asyncio.to_thread(download_media, arg, MEDIA_DIR / label / "downloads")
                    await client.send_file(event.chat_id, path)
                    await event.delete()
            elif cmd == "meta":
                await event.edit("\n".join(f"{k}: {v}" for k, v in (await asyncio.to_thread(extract_metadata, arg)).items()) if arg else "Usage: .meta <url>")
            elif cmd == "s":
                reply = await event.get_reply_message()
                if not reply or not reply.media:
                    await event.edit("Reply to image/sticker with .s")
                else:
                    tmp = MEDIA_DIR / label / "tmp"; tmp.mkdir(parents=True, exist_ok=True)
                    src = Path(await reply.download_media(file=tmp / "src"))
                    out = image_to_sticker(src, tmp / "sticker.webp")
                    await client.send_file(event.chat_id, out)
                    await event.delete()
            elif cmd == "toimg":
                reply = await event.get_reply_message()
                if not reply or not reply.media:
                    await event.edit("Reply to sticker with .toimg")
                else:
                    tmp = MEDIA_DIR / label / "tmp"; tmp.mkdir(parents=True, exist_ok=True)
                    src = Path(await reply.download_media(file=tmp / "st"))
                    out = sticker_to_image(src, tmp / "st.png")
                    await client.send_file(event.chat_id, out)
                    await event.delete()
            elif cmd == "tagall":
                if not event.is_group:
                    await event.edit("Group only")
                else:
                    out = []
                    async for u in client.iter_participants(event.chat_id):
                        out.append(f"[{u.first_name}](tg://user?id={u.id})")
                        if len(out) >= 40:
                            break
                    await event.edit(" ".join(out))
            elif cmd in {"kick", "promote", "demote"}:
                if not event.is_group:
                    await event.edit("Group only")
                else:
                    target = arg.strip() or ((await event.get_reply_message()).sender_id if event.is_reply else None)
                    if not target:
                        await event.edit(f"Usage: .{cmd} @user")
                    else:
                        ent = await client.get_input_entity(target)
                        if cmd == "kick":
                            await client.kick_participant(event.chat_id, ent)
                        elif cmd == "promote":
                            await client.edit_admin(event.chat_id, ent, is_admin=True, ban_users=True)
                        else:
                            await client.edit_admin(event.chat_id, ent, is_admin=False)
                        await event.edit(f"{cmd} done")
            elif cmd == "pin":
                rm = await event.get_reply_message()
                await client.pin_message(event.chat_id, rm.id) if rm else await event.edit("Reply then .pin")
            elif cmd == "unpin":
                await client.unpin_message(event.chat_id)
                await event.delete()
            elif cmd == "logout":
                d = store.load_user(label); d["active"] = False; store.save_user(label, d)
                await event.edit("Logged out (inactive)")
            elif cmd == "reset":
                store.delete_user(label)
                await event.edit("Profile deleted")
            else:
                await event.edit("Unknown command. Use .menu")
            logger.info("[cmd] %s -> %s %s", label, cmd, arg)
        except Exception as exc:
            logger.exception("[cmd-error] %s %s :: %s", label, cmd, exc)
            await event.edit(f"Error: {exc}\nUse .menu")


async def start_client(label: str, profile: dict):
    client = TelegramClient(StringSession(profile["string_session"]), profile["api_id"], profile["api_hash"])
    await client.start()
    me = await client.get_me()
    logger.info("[online] %s as %s (%s)", label, me.first_name, me.id)
    await register_handlers(client, label)
    return client


async def main():
    labels = store.list_users()
    if not labels:
        print("No user accounts found. Run: python frontend.py")
        return
    clients = []
    for label in labels:
        p = store.load_user(label)
        if not p.get("active", True):
            continue
        try:
            clients.append(await start_client(label, p))
        except Exception as exc:
            logger.exception("[startup-error] %s :: %s", label, exc)
    if not clients:
        print("No active clients started.")
        return
    print(f"Started {len(clients)} userbot client(s). Ctrl+C to stop.")
    await asyncio.gather(*[c.run_until_disconnected() for c in clients])


if __name__ == "__main__":
    asyncio.run(main())
