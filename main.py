from __future__ import annotations

import asyncio
import json
import os
import random
import re
import shutil
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from pathlib import Path

import httpx
from telethon import TelegramClient, events, functions, types, errors
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
• `.getsettings` → view current feature toggles/status
• `.restart` → pull updates + restart service

**Automation**
• `.away <text>` / `.away off` → AFK auto-reply
• `.schedule <10m|HH:MM> <message>` → send later
• `.filter <word> <response>` → keyword auto-reply

**Privacy / Logs**
• `.anti-delete on|off`
• `.anti-edit on|off`

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
• `.msg <username/group> <text>` or reply + `.msg <target>`
• `.decodeid <id>` or reply log + `.decodeid`
• `.iscypherus <@user/id>`
• `.search <text>`
• `.setpin <pin>` `.changepin <old> <new>`
• `.hide <target> <pin>` `.unhide <target> <pin>`

**Group Admin**
• `.tagall`
• `.kick @user` `.promote @user` `.demote @user`
• `.warn @user` `.mute @user 10m`
• `.join <invite_link>`
• `.pin` / `.unpin`

**Smart / Viral / Utility+**
• `.persona calm|savage|default` `.generate` `.code` `.teach`
• `.roast @user` `.ship @u1 @u2` `.rate @user` `.vibecheck` `.truth` `.dare`
• `.lockchat on|off` `.blockword <word>` `.stats` `.activity @user` `.usage`
• `.backup` `.restore` `.save <name>` (reply) `.get <name>` `.list`
• `.daily` `.rank` `.genpass`

**Extra Aliases / Search / Settings**
• `.tiktok` `.instagram` `.twitter` `.video` `.song`
• `.qrcode` `.tinyurl` `.sticker` `.toimage` `.tourl`
• `.lyrics` `.define` `.weather` `.jokes` `.memes` `.quotes`
• `.setprefix` `.setbotname` `.setownername`
• `.autoread on|off` `.autotype on|off` `.alwaysonline on|off`
• `.setwelcome <text>` `.setgoodbye <text>` `.link`
• `.autostoryview on|off` `.autostoryreact on|off`
"""



COMMAND_HELP = {
    "menu": "Usage: .menu\nShow full command menu.",
    "ping": "Usage: .ping\nCheck response speed.",
    "getsettings": "Usage: .getsettings\nShow ON/OFF + key settings overview.",
    "restart": "Usage: .restart\nPull updates and restart process.",
    "unlinktoken": "Usage: .unlinktoken\nRemove saved control-bot token.",
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
    "msg": "Usage: .msg <target> <text> OR reply + .msg <target>\nSend message/media to user/group.",
    "decodeid": "Usage: .decodeid <id> OR reply + .decodeid\nResolve ID to username/title/type.",
    "iscypherus": "Usage: .iscypherus <@user/id>\nCheck whether user is linked in local Cypherus accounts.",
    "search": "Usage: .search <text>\nSearch and preview media results.",
    "setpin": "Usage: .setpin <pin>\nSet hidden-chat security PIN.",
    "changepin": "Usage: .changepin <oldpin> <newpin>\nChange hidden-chat PIN.",
    "hide": "Usage: .hide <target> <pin>\nHide chat using Cypherus vault mode.",
    "unhide": "Usage: .unhide <target> <pin>\nRestore hidden chat to normal list.",
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
    "generate": "Usage: .generate <prompt>\nGenerate stories/captions/scripts.",
    "code": "Usage: .code <task>\nGenerate or fix code.",
    "teach": "Usage: .teach <topic>\nExplain step-by-step.",
    "tiktok": "Usage: .tiktok <url>\nDownload TikTok video.",
    "instagram": "Usage: .instagram <url>\nDownload Instagram video/reel.",
    "twitter": "Usage: .twitter <url>\nDownload Twitter/X video.",
    "video": "Usage: .video <url>\nDownload supported video URL.",
    "link": "Usage: .link\nGet group invite link.",
    "setwelcome": "Usage: .setwelcome <text>\nSet group welcome message.",
    "setgoodbye": "Usage: .setgoodbye <text>\nSet group goodbye message.",
    "setprefix": "Usage: .setprefix <symbol>\nSet command prefix.",
    "setbotname": "Usage: .setbotname <name>\nSet bot display name setting.",
    "setownername": "Usage: .setownername <name>\nSet owner name setting.",
    "autoread": "Usage: .autoread on|off\nAuto mark chats as read.",
    "autotype": "Usage: .autotype on|off\nSend typing action.",
    "alwaysonline": "Usage: .alwaysonline on|off\nAttempt always-online status.",
    "qrcode": "Usage: .qrcode <text>\nGenerate QR code.",
    "tinyurl": "Usage: .tinyurl <url>\nShorten URL.",
    "sticker": "Usage: reply image + .sticker\nConvert image to sticker.",
    "toimage": "Usage: reply sticker + .toimage\nConvert sticker to image.",
    "tourl": "Usage: reply file + .tourl\nUpload file and get public link.",
    "genpass": "Usage: .genpass\nGenerate random strong password.",
    "lyrics": "Usage: .lyrics artist - song\nFetch song lyrics.",
    "define": "Usage: .define <word>\nDictionary meaning.",
    "weather": "Usage: .weather <city>\nCurrent weather.",
    "jokes": "Usage: .jokes\nRandom joke.",
    "memes": "Usage: .memes\nRandom meme image.",
    "quotes": "Usage: .quotes\nMotivational quote.",
    "autostoryview": "Usage: .autostoryview on|off\nAuto-view new stories.",
    "autostoryreact": "Usage: .autostoryreact on|off\nAuto-react to viewed stories.",
}


def resolve_help(query: str) -> str:
    q = query.strip().lower().lstrip('.')
    if not q:
        return HELP_TEXT + "\n\nTip: .help <command>  (example: .help vvwatch)"
    if q in COMMAND_HELP:
        return (
            f"**.{q}**\n{COMMAND_HELP[q]}\n\n"
            "Explanation: This command is part of Cypherus workflow. Read the usage exactly, include required arguments, and if needed reply to a message first. "
            "If it fails, check permissions, target format, and try again with .help for that command."
        )
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
    s.setdefault("anti_delete", False)
    s.setdefault("anti_edit", False)
    s.setdefault("vvwatch", True)
    s.setdefault("warns", {})
    s.setdefault("persona", "default")
    s.setdefault("smart_ai", False)
    s.setdefault("chat_memory", {})
    s.setdefault("lockchat", False)
    s.setdefault("blockwords", [])
    s.setdefault("stats", {"messages_seen": 0, "messages_sent": 0, "commands": 0, "chat_hits": {}})
    s.setdefault("saved_items", {})
    s.setdefault("xp", {"points": 0, "daily_last": ""})
    s.setdefault("prefix", ".")
    s.setdefault("botname", "Cypherus")
    s.setdefault("ownername", "Owner")
    s.setdefault("autoread", False)
    s.setdefault("autotype", False)
    s.setdefault("alwaysonline", False)
    s.setdefault("welcome", {})
    s.setdefault("goodbye", {})
    s.setdefault("vault_pin", "")
    s.setdefault("hidden_chats", {})
    s.setdefault("autostory_view", False)
    s.setdefault("autostory_react", False)


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



async def fetch_text_search(kind: str, query: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=25) as c:
            if kind == "lyrics":
                parts = query.split("-", 1)
                if len(parts) < 2:
                    return "Use: .lyrics artist - title"
                r = await c.get(f"https://api.lyrics.ovh/v1/{parts[0].strip()}/{parts[1].strip()}")
                if r.is_success:
                    return (r.json().get("lyrics") or "No lyrics found")[:3900]
            elif kind == "define":
                r = await c.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{query.strip()}")
                if r.is_success:
                    d = r.json()[0]
                    m = d.get("meanings", [{}])[0].get("definitions", [{}])[0].get("definition", "No definition")
                    return f"{query}: {m}"
            elif kind == "weather":
                r = await c.get(f"https://wttr.in/{query}?format=j1")
                if r.is_success:
                    d = r.json().get("current_condition", [{}])[0]
                    return f"{query}: {d.get('temp_C')}°C, {d.get('weatherDesc',[{'value':''}])[0]['value']}"
    except Exception:
        pass
    return f"{kind} unavailable"


def get_user_prefix(label: str) -> str:
    try:
        d = store.load_user(label)
        ensure_settings(d)
        return d["settings"].get("prefix", ".") or "."
    except Exception:
        return "."



async def story_auto_worker(client: TelegramClient, label: str):
    while True:
        try:
            data = store.load_user(label)
            ensure_settings(data)
            st = data["settings"]
            if st.get("autostory_view", False):
                stories_api = getattr(functions, "stories", None)
                if stories_api:
                    async for dlg in client.iter_dialogs():
                        if not dlg.is_user:
                            return
                        try:
                            req = stories_api.ReadStoriesRequest(peer=dlg.entity, max_id=2_147_483_647)
                            await client(req)
                            if st.get("autostory_react", False):
                                # best-effort reaction endpoint; ignore if unavailable
                                send_react = getattr(stories_api, "SendReactionRequest", None)
                                get_peer = getattr(stories_api, "GetPeerStoriesRequest", None)
                                if send_react and get_peer:
                                    peer_stories = await client(get_peer(peer=dlg.entity))
                                    stories_obj = getattr(peer_stories, "stories", None)
                                    if stories_obj and getattr(stories_obj, "stories", None):
                                        for st_item in stories_obj.stories[:3]:
                                            sid = getattr(st_item, "id", None)
                                            if sid:
                                                await client(send_react(peer=dlg.entity, story_id=sid, reaction=types.ReactionEmoji(emoticon="❤️"), add_to_recent=True))
                        except Exception:
                            return
        except Exception:
            pass
        await asyncio.sleep(60)

async def register_handlers(client: TelegramClient, label: str):
    anti_spam_map: dict[int, deque[float]] = defaultdict(deque)
    msg_cache: dict[tuple[int, int], dict] = {}

    @client.on(events.NewMessage(incoming=True))
    async def incoming_handler(event):
        msg = event.message
        data = store.load_user(label)
        ensure_settings(data)
        settings = data["settings"]
        if settings.get("autoread", False):
            await client.send_read_acknowledge(event.chat_id, msg)
        if settings.get("autotype", False) and event.is_private:
            await client(functions.messages.SetTypingRequest(peer=event.chat_id, action=types.SendMessageTypingAction()))
        if settings.get("alwaysonline", False):
            try:
                await client(functions.account.UpdateStatusRequest(offline=False))
            except Exception:
                pass
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

    
    @client.on(events.ChatAction)
    async def on_chat_action(event):
        data = store.load_user(label)
        ensure_settings(data)
        chat_key = str(event.chat_id)
        if event.user_joined or event.user_added:
            text = data["settings"].get("welcome", {}).get(chat_key)
            if text:
                await event.reply(text)
        if event.user_left or event.user_kicked:
            text = data["settings"].get("goodbye", {}).get(chat_key)
            if text:
                await event.reply(text)
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

    @client.on(events.NewMessage(outgoing=True))
    async def command_handler(event):
        prefix = get_user_prefix(label)
        if not (event.raw_text or "").startswith(prefix):
            return
        cmd, arg = parse_command((event.raw_text or "").replace(prefix, ".", 1))
        if not cmd:
            return
        try:
            data = store.load_user(label)
            ensure_settings(data)
            data["settings"]["stats"]["commands"] = int(data["settings"]["stats"].get("commands", 0)) + 1
            data["settings"]["stats"]["messages_sent"] = int(data["settings"]["stats"].get("messages_sent", 0)) + 1
            store.save_user(label, data)

            removed_cmds = {"persona","generate","code","teach","roast","ship","rate","vibecheck","truth","dare","lockchat","blockword","stats","activity","usage","daily","rank","genpass","video","jokes","memes","weather","define","tourl","ghostmode","hideonline"}
            if cmd in removed_cmds:
                await event.edit("This feature was removed in current build.")
                return

            if cmd in {"help", "menu"}:
                await event.edit(resolve_help(arg if cmd == "help" else ""))
            elif cmd == "restart":
                await event.edit("Updating and restarting...")
                import subprocess, sys
                try:
                    pull = await asyncio.to_thread(subprocess.run, ["git", "pull"], capture_output=True, text=True)
                    req = await asyncio.to_thread(subprocess.run, [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], capture_output=True, text=True)
                    msg = f"git: {pull.returncode}\n{(pull.stdout or pull.stderr)[-500:]}\npip: {req.returncode}"
                    if req.returncode != 0:
                        msg += "\nDependency install failed. Please install manually then restart."
                        await event.edit(msg[:3900])
                        return
                    await event.edit((msg + "\nRestarting now...")[:3900])
                    os.execv(sys.executable, [sys.executable, "main.py"])
                except Exception as exc:
                    await event.edit(f"Restart failed: {exc}")

            elif cmd == "unlinktoken":
                tok = USERS_DIR / ".control_token"
                if tok.exists():
                    tok.unlink()
                    await event.edit("Saved control token removed.")
                else:
                    await event.edit("No saved control token.")

            elif cmd == "ping":
                t0 = time.perf_counter()
                msg = await event.respond("🏓 Pong...")
                ms = (time.perf_counter() - t0) * 1000
                await msg.edit(f"🏓 Pong: {ms:.2f} ms")
                await event.delete()

            elif cmd in {"vet", "getsettings"}:
                d = store.load_user(label)
                ensure_settings(d)
                st = d["settings"]
                lines = [
                    "**Cypherus Status (.vet)**",
                    f"prefix: {st.get('prefix', '.')}",
                    f"persona: {st.get('persona', 'default')}",
                    f"autoread: {'ON' if st.get('autoread') else 'OFF'}",
                    f"autotype: {'ON' if st.get('autotype') else 'OFF'}",
                    f"alwaysonline: {'ON' if st.get('alwaysonline') else 'OFF'}",
                    f"away: {'ON' if st.get('away', {}).get('enabled') else 'OFF'}",
                    f"antispam: {'ON' if st.get('antispam', {}).get('enabled') else 'OFF'}",
                    f"anti-delete: {'ON' if st.get('anti_delete') else 'OFF'}",
                    f"anti-edit: {'ON' if st.get('anti_edit') else 'OFF'}",
                    f"vvwatch: {'ON' if st.get('vvwatch') else 'OFF'}",
                    f"autostoryview: {'ON' if st.get('autostory_view') else 'OFF'}",
                    f"autostoryreact: {'ON' if st.get('autostory_react') else 'OFF'}",
                    f"lockchat: {'ON' if st.get('lockchat') else 'OFF'}",
                    f"filters: {len(st.get('filters', {}))}",
                    f"blocked words: {len(st.get('blockwords', []))}",
                    f"hidden chats: {len(st.get('hidden_chats', {}))}",
                ]
                await event.edit("\n".join(lines)[:3900])

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

            elif cmd in {"persona","generate","code","teach","roast","ship","rate","vibecheck","truth","dare","lockchat","blockword","stats","activity","usage","daily","rank","genpass","video","jokes","memes","weather","define","tourl"}:
                await event.edit("This feature was removed in current build.")

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

            elif cmd in {"generate", "code", "teach"}:
                if not arg.strip():
                    await event.edit(f"Usage: .{cmd} <prompt>")
                else:
                    prompt = {
                        "generate": f"Generate creative content for: {arg}",
                        "code": f"Write/fix code for: {arg}",
                        "teach": f"Teach step-by-step: {arg}",
                    }[cmd]
                    d = store.load_user(label); ensure_settings(d)
                    out = await ask_free_ai(prompt, d["settings"].get("persona", "default"), [])
                    await event.edit(out[:3900])

            elif cmd in {"tiktok", "instagram", "twitter", "video"}:
                if not arg:
                    await event.edit(f"Usage: .{cmd} <url>")
                else:
                    await event.edit("Downloading...")
                    path = await asyncio.to_thread(download_media, arg, MEDIA_DIR / label / "downloads")
                    await client.send_file(event.chat_id, path)
                    await event.delete()

            elif cmd == "link":
                if not event.is_group:
                    await event.edit("Group only")
                else:
                    full = await client(functions.messages.ExportChatInviteRequest(event.chat_id))
                    await event.edit(getattr(full, "link", "Cannot get link"))

            elif cmd == "setwelcome":
                if not event.is_group or not arg.strip():
                    await event.edit("Usage: .setwelcome <text> (in group)")
                else:
                    def m(d):
                        ensure_settings(d)
                        d["settings"].setdefault("welcome", {})[str(event.chat_id)] = arg.strip()
                    await update_user_settings(label, m)
                    await event.edit("Welcome message set.")

            elif cmd == "setgoodbye":
                if not event.is_group or not arg.strip():
                    await event.edit("Usage: .setgoodbye <text> (in group)")
                else:
                    def m(d):
                        ensure_settings(d)
                        d["settings"].setdefault("goodbye", {})[str(event.chat_id)] = arg.strip()
                    await update_user_settings(label, m)
                    await event.edit("Goodbye message set.")

            elif cmd in {"setprefix", "setbotname", "setownername"}:
                if not arg.strip():
                    await event.edit(f"Usage: .{cmd} <value>")
                else:
                    def m(d):
                        ensure_settings(d)
                        if cmd == "setprefix":
                            d["settings"]["prefix"] = arg.strip()[0]
                        elif cmd == "setbotname":
                            d["settings"]["botname"] = arg.strip()
                        else:
                            d["settings"]["ownername"] = arg.strip()
                    await update_user_settings(label, m)
                    await event.edit(f"{cmd} updated.")

            elif cmd in {"autoread", "autotype", "alwaysonline"}:
                st = arg.strip().lower()
                if st not in {"on", "off"}:
                    await event.edit(f"Usage: .{cmd} on|off")
                else:
                    def m(d):
                        ensure_settings(d)
                        d["settings"][cmd] = st == "on"
                    await update_user_settings(label, m)
                    await event.edit(f"{cmd} {st}")

            elif cmd in {"qrcode", "tinyurl", "sticker", "toimage"}:
                alias = {"qrcode": "qr", "tinyurl": "short", "sticker": "s", "toimage": "toimg"}[cmd]
                cmd = alias
                # fall through via manual dispatch
                if cmd == "qr":
                    if not arg:
                        await event.edit("Usage: .qrcode <text>")
                    else:
                        await event.edit("Creating your QR...")
                        await client.send_file(event.chat_id, await build_qr_png_bytes(arg), caption="QR", file_name="qrcode.png")
                        await event.delete()
                elif cmd == "short":
                    await event.edit(await shorten_url(arg) if arg else "Usage: .tinyurl <url>")
                elif cmd == "s":
                    reply = await event.get_reply_message()
                    if not reply or not reply.media:
                        await event.edit("Reply image + .sticker")
                    else:
                        tmp = MEDIA_DIR / label / "tmp"; tmp.mkdir(parents=True, exist_ok=True)
                        src = Path(await reply.download_media(file=tmp / "src"))
                        out = image_to_sticker(src, tmp / "sticker.webp")
                        await client.send_file(event.chat_id, out); await event.delete()
                else:
                    reply = await event.get_reply_message()
                    if not reply or not reply.media:
                        await event.edit("Reply sticker + .toimage")
                    else:
                        tmp = MEDIA_DIR / label / "tmp"; tmp.mkdir(parents=True, exist_ok=True)
                        src = Path(await reply.download_media(file=tmp / "sti"))
                        out = sticker_to_image(src, tmp / "sti.png")
                        await client.send_file(event.chat_id, out); await event.delete()

            elif cmd == "tourl":
                reply = await event.get_reply_message()
                if not reply or not reply.media:
                    await event.edit("Usage: reply file + .tourl")
                else:
                    tmp = MEDIA_DIR / label / "tmp"; tmp.mkdir(parents=True, exist_ok=True)
                    src = Path(await reply.download_media(file=tmp / "upload_file"))
                    async with httpx.AsyncClient(timeout=40) as c:
                        files = {"file": (src.name, src.read_bytes())}
                        r = await c.post("https://0x0.st", files=files)
                        await event.edit(r.text.strip() if r.is_success else "Upload failed")

            elif cmd == "genpass":
                import secrets, string
                chars = string.ascii_letters + string.digits + "!@#$%^&*"
                pwd = "".join(secrets.choice(chars) for _ in range(16))
                await event.edit(f"Generated password: `{pwd}`")

            elif cmd in {"lyrics", "define", "weather"}:
                if not arg:
                    await event.edit(f"Usage: .{cmd} <query>")
                else:
                    await event.edit((await fetch_text_search(cmd, arg))[:3900])

            elif cmd in {"jokes", "quotes", "memes"}:
                if cmd == "memes":
                    async with httpx.AsyncClient(timeout=20) as c:
                        r = await c.get("https://meme-api.com/gimme")
                        if r.is_success:
                            d = r.json()
                            await client.send_file(event.chat_id, d.get("url"), caption=d.get("title", "meme"))
                            await event.delete()
                        else:
                            await event.edit("Meme unavailable")
                else:
                    await event.edit(await fetch_fun_text("joke" if cmd == "jokes" else "quote"))

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

            elif cmd in {"anti-delete", "anti-edit", "vvwatch", "antispam", "autostoryview", "autostoryreact"}:
                state = arg.strip().lower()
                if state not in {"on", "off"}:
                    await event.edit(f"Usage: .{cmd} on|off")
                    return
                key = cmd.replace("-", "_")
                if key == "autostoryview":
                    key = "autostory_view"
                if key == "autostoryreact":
                    key = "autostory_react"
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
                files = sorted(outdir.glob("*"), key=lambda p: p.stat().st_mtime)
                if not files:
                    await event.edit("Playlist download completed but no files found.")
                else:
                    await event.edit(f"Playlist download completed. Sending {len(files)} file(s)...")
                    for f in files[:20]:
                        try:
                            await client.send_file(event.chat_id, f)
                        except Exception:
                            pass
                    await event.delete()

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
                    with yt_dlp.YoutubeDL({"format": "bestaudio/best", "outtmpl": str(outdir / "%(title).70s.%(ext)s"), "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}], "noplaylist": True}) as y:
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
                    await event.edit("Usage: .join <invite_link_or_username>")
                    return
                link = arg.strip()
                try:
                    if "joinchat/" in link or "/+" in link or link.startswith("https://t.me/+"):
                        h = link.split("+")[-1].split("?")[0].split("/")[-1]
                        await client(functions.messages.ImportChatInviteRequest(hash=h))
                    else:
                        username = link.replace("https://t.me/", "").lstrip("@")
                        await client(functions.channels.JoinChannelRequest(channel=username))
                    await event.edit("Joined.")
                except Exception as exc:
                    await event.edit(f"Join failed: {exc}")

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

            elif cmd == "setpin":
                pin = arg.strip()
                if not pin:
                    await event.edit("Usage: .setpin <pin>")
                    return
                def m(d):
                    ensure_settings(d)
                    d["settings"]["vault_pin"] = pin
                await update_user_settings(label, m)
                await event.edit("Vault PIN set.")

            elif cmd == "changepin":
                parts = arg.split(maxsplit=1)
                if len(parts) < 2:
                    await event.edit("Usage: .changepin <oldpin> <newpin>")
                    return
                old, new = parts[0], parts[1]
                d = store.load_user(label); ensure_settings(d)
                current = d["settings"].get("vault_pin", "")
                if not current:
                    await event.edit("No PIN set yet. Use .setpin first.")
                    return
                if old != current:
                    await event.edit("Wrong old PIN.")
                    return
                d["settings"]["vault_pin"] = new
                store.save_user(label, d)
                await event.edit("PIN changed.")

            elif cmd in {"hide", "unhide"}:
                parts = arg.split(maxsplit=1)
                if len(parts) < 2:
                    await event.edit(f"Usage: .{cmd} <target> <pin>")
                    return
                target, pin = parts[0], parts[1].strip()
                d = store.load_user(label); ensure_settings(d)
                vault_pin = d["settings"].get("vault_pin", "")
                if not vault_pin:
                    await event.edit("No PIN set. Use .setpin first.")
                    return
                if pin != vault_pin:
                    await event.edit("Invalid PIN.")
                    return
                try:
                    ent = await client.get_entity(target)
                    inp = await client.get_input_entity(ent)
                    hid = d["settings"].setdefault("hidden_chats", {})
                    key = str(ent.id)
                    if cmd == "hide":
                        if key in hid:
                            await event.edit("That chat is already hidden.")
                            return
                        hid[key] = {"title": getattr(ent, "title", None) or getattr(ent, "first_name", None) or target, "blocked": False}
                        await event.edit("Chat flagged as hidden in Cypherus vault database (non-destructive).")
                    else:
                        if key not in hid:
                            await event.edit("That chat was not hidden.")
                            return
                        hid.pop(key, None)
                        await event.edit("Chat unhidden and restored in Cypherus vault database.")
                    store.save_user(label, d)
                except Exception as exc:
                    await event.edit(f"Failed: {exc}")

            elif cmd == "decodeid":
                reply = await event.get_reply_message() if event.is_reply else None
                raw = arg.strip() or (reply.raw_text if reply else "")
                ids = re.findall(r"-?\d+", raw)
                if not ids:
                    await event.edit("Usage: .decodeid <id> OR reply to log with .decodeid")
                    return
                dialog_map = {}
                async for dlg in client.iter_dialogs(limit=300):
                    dialog_map[dlg.id] = dlg.entity
                out = []
                for x in ids[:8]:
                    xi = int(x)
                    try:
                        ent = await client.get_entity(xi)
                        title = getattr(ent, "title", None) or getattr(ent, "first_name", None) or "Unknown"
                        uname = getattr(ent, "username", None)
                        etype = ent.__class__.__name__
                        out.append(f"{x} -> {title} | @{uname if uname else '-'} | {etype}")
                    except Exception as exc:
                        ent = dialog_map.get(xi)
                        if ent:
                            title = getattr(ent, "title", None) or getattr(ent, "first_name", None) or "Unknown"
                            uname = getattr(ent, "username", None)
                            etype = ent.__class__.__name__
                            out.append(f"{x} -> {title} | @{uname if uname else '-'} | {etype} (from dialogs)")
                        elif xi > 0:
                            out.append(f"{x} -> User ID exists but not accessible (not in contacts/mutual chats)")
                        else:
                            out.append(f"{x} -> unresolved ({exc})")
                await event.edit("\n".join(out)[:3900])

            elif cmd == "iscypherus":
                if not arg.strip():
                    await event.edit("Usage: .iscypherus <@user/id>")
                    return
                try:
                    ent = await client.get_entity(arg.strip())
                    uid = getattr(ent, "id", None)
                    found = []
                    for lb in store.list_users():
                        d = store.load_user(lb)
                        if d.get("user_id") == uid:
                            found.append(lb)
                    if found:
                        await event.edit(f"✅ {arg.strip()} is linked in Cypherus as: {', '.join(found)}")
                    else:
                        await event.edit("❌ Not found in local Cypherus linked accounts.")
                except Exception as exc:
                    await event.edit(f"Failed: {exc}")

            elif cmd in {"search", "ytsearch"}:
                if not arg.strip():
                    await event.edit("Usage: .ytsearch <text>")
                    return
                await event.edit("Searching...")
                import yt_dlp
                def _search(q):
                    with yt_dlp.YoutubeDL({"quiet": True}) as y:
                        return y.extract_info(f"ytsearch5:{q}", download=False)
                info = await asyncio.to_thread(_search, arg.strip())
                entries = info.get("entries", [])[:5]
                if not entries:
                    await event.edit("No results.")
                else:
                    lines = ["🔎 Search results:"]
                    for i, e in enumerate(entries, 1):
                        lines.append(f"{i}. {e.get('title')}\n{e.get('webpage_url')}")
                    await event.edit("\n\n".join(lines)[:3900])

            elif cmd == "ggsearch":
                if not arg.strip():
                    await event.edit("Usage: .ggsearch <text>")
                    return
                await event.edit("Searching web...")
                async with httpx.AsyncClient(timeout=20) as x:
                    r = await x.get("https://api.duckduckgo.com/", params={"q": arg.strip(), "format": "json", "no_html": 1})
                    if r.is_success:
                        d = r.json()
                        ans = d.get("AbstractText") or d.get("Answer") or "No instant answer."
                        await event.edit(ans[:3900])
                    else:
                        await event.edit("Search failed.")

            elif cmd == "msg":
                parts = arg.split(maxsplit=1)
                if not parts:
                    await event.edit("Usage: .msg <target> <text> OR reply + .msg <target>")
                    return
                target = parts[0]
                text_body = parts[1] if len(parts) > 1 else ""
                reply = await event.get_reply_message() if event.is_reply else None
                try:
                    entity = await client.get_entity(target)
                    if reply and reply.media:
                        tmp = MEDIA_DIR / label / "tmp"
                        tmp.mkdir(parents=True, exist_ok=True)
                        src = await reply.download_media(file=tmp / "msg_forward")
                        caption = text_body or (reply.raw_text or "")
                        await client.send_file(entity, src, caption=caption)
                    elif reply and (reply.raw_text and not text_body):
                        await client.send_message(entity, reply.raw_text)
                    elif text_body:
                        await client.send_message(entity, text_body)
                    else:
                        await event.edit("Nothing to send. Add text or reply to message/media.")
                        return
                    await event.edit("Sent ✅")
                except Exception as exc:
                    await event.edit(f"Failed to send: {exc}")

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
            elif cmd in {"logout", "reset"}:
                await event.edit("This command was removed. Use control bot to manage accounts.")
            else:
                await event.edit("Unknown command. Use .menu")
            logger.info("[cmd] %s -> %s %s", label, cmd, arg)
        except Exception as exc:
            logger.exception("[cmd-error] %s %s :: %s", label, cmd, exc)
            await event.edit(f"Error: {exc}\nUse .menu")




async def start_control_bot() -> asyncio.Task | None:
    token_file = USERS_DIR / ".control_token"
    token = os.getenv("CONTROL_BOT_TOKEN")
    if not token and token_file.exists():
        token = token_file.read_text(encoding="utf-8").strip()
    if not token:
        token = input("Enter control bot token (or leave blank to skip): ").strip()
        if token:
            token_file.write_text(token, encoding="utf-8")
    if not token:
        print("No control bot token. Continuing without controller bot.")
        return None

    api_base = f"https://api.telegram.org/bot{token}"
    ctrl_file = USERS_DIR / ".controller.json"
    owner_id = None
    if ctrl_file.exists():
        try:
            owner_id = json.loads(ctrl_file.read_text()).get("owner_id")
        except Exception:
            owner_id = None

    pending_add: dict[int, dict] = {}
    pending_phone: dict[int, dict] = {}
    pending_action: dict[int, dict] = {}

    MENU_KEYS = [["➕ Add Account (Phone)", "➕ Add Account (Session)"], ["📋 List Accounts", "✅ Enable Account"], ["⛔ Disable Account", "🗑 Delete Account"], ["❌ Cancel", "🏠 Menu"], ["🔓 Unlink Token"]]

    async def send_msg(client: httpx.AsyncClient, chat_id: int, text: str, menu: bool = False):
        payload = {"chat_id": chat_id, "text": text}
        if menu:
            payload["reply_markup"] = {"keyboard": MENU_KEYS, "resize_keyboard": True, "one_time_keyboard": False}
        await client.post(f"{api_base}/sendMessage", json=payload)

    async def poll_loop():
        nonlocal owner_id
        offset = 0
        async with httpx.AsyncClient(timeout=35) as client:
            while True:
                try:
                    res = await client.get(f"{api_base}/getUpdates", params={"timeout": 10, "offset": offset})
                    data = res.json()
                    if not data.get("ok"):
                        await asyncio.sleep(2)
                        continue
                    for upd in data.get("result", []):
                        offset = max(offset, upd["update_id"] + 1)
                        msg = upd.get("message") or {}
                        text = (msg.get("text") or "").strip()
                        chat = msg.get("chat") or {}
                        chat_id = chat.get("id")
                        sender = msg.get("from") or {}
                        sender_id = sender.get("id")
                        if not chat_id or not sender_id:
                            continue

                        if owner_id is None:
                            owner_id = sender_id
                            ctrl_file.write_text(json.dumps({"owner_id": owner_id}, indent=2))
                        if sender_id != owner_id:
                            continue

                        if text == "🔓 Unlink Token":
                            tf = USERS_DIR / ".control_token"
                            if tf.exists():
                                tf.unlink()
                                await send_msg(client, chat_id, "Saved token unlinked.", menu=True)
                            else:
                                await send_msg(client, chat_id, "No saved token.", menu=True)
                            continue

                        if text in {"🏠 Menu", "menu", "Menu"}:
                            await send_msg(client, chat_id, "Main menu:", menu=True)
                            continue

                        if text == "❌ Cancel":
                            pending_add.pop(chat_id, None)
                            pending_phone.pop(chat_id, None)
                            pending_action.pop(chat_id, None)
                            await send_msg(client, chat_id, "Cancelled.", menu=True)
                            continue

                        if text in {"➕ Add Account (Phone)", "/add_account_phone"}:
                            pending_phone[chat_id] = {"step": "label"}
                            pending_add.pop(chat_id, None)
                            pending_action.pop(chat_id, None)
                            await send_msg(client, chat_id, "Phone wizard 1/6: send account label")
                            continue

                        if text in {"➕ Add Account (Session)", "/add_account"}:
                            pending_add[chat_id] = {"step": "label"}
                            pending_phone.pop(chat_id, None)
                            pending_action.pop(chat_id, None)
                            await send_msg(client, chat_id, "Session wizard 1/4: send account label")
                            continue

                        if text == "📋 List Accounts":
                            labels = store.list_users()
                            if not labels:
                                await send_msg(client, chat_id, "No users.", menu=True)
                            else:
                                lines = []
                                for lb in labels:
                                    d = store.load_user(lb)
                                    lines.append(f"{lb} active={d.get('active', True)}")
                                await send_msg(client, chat_id, "\n".join(lines), menu=True)
                            continue

                        if text in {"✅ Enable Account", "⛔ Disable Account", "🗑 Delete Account"}:
                            mode = {"✅ Enable Account": "enable", "⛔ Disable Account": "disable", "🗑 Delete Account": "delete"}[text]
                            pending_action[chat_id] = {"mode": mode}
                            await send_msg(client, chat_id, f"Send label to {mode}:")
                            continue

                        if chat_id in pending_action:
                            mode = pending_action[chat_id]["mode"]
                            label = text.strip()
                            if mode == "delete":
                                store.delete_user(label)
                                await send_msg(client, chat_id, f"Deleted {label}", menu=True)
                            else:
                                try:
                                    d = store.load_user(label)
                                    d["active"] = mode == "enable"
                                    store.save_user(label, d)
                                    await send_msg(client, chat_id, f"{label} active={d['active']}", menu=True)
                                except Exception as exc:
                                    await send_msg(client, chat_id, f"Error: {exc}", menu=True)
                            pending_action.pop(chat_id, None)
                            continue

                        if text == "/start":
                            await send_msg(
                                client,
                                chat_id,
                                "Controller ready.\n"
                                "/add_account (interactive, with StringSession)\n/add_account_phone (interactive, login by phone)\n"
                                "/list\n/enable <label>\n/disable <label>\n/delete <label>\n"
                                "Use buttons below (preferred).",
                                menu=True,
                            )
                            continue


                        if chat_id in pending_add:
                            st = pending_add[chat_id]
                            step = st.get("step")
                            if step == "label":
                                st["label"] = text
                                st["step"] = "api_id"
                                await send_msg(client, chat_id, "Step 2/4: send api_id")
                            elif step == "api_id":
                                try:
                                    st["api_id"] = int(text)
                                    st["step"] = "api_hash"
                                    await send_msg(client, chat_id, "Step 3/4: send api_hash")
                                except ValueError:
                                    await send_msg(client, chat_id, "api_id must be integer.")
                            elif step == "api_hash":
                                st["api_hash"] = text
                                st["step"] = "string_session"
                                await send_msg(client, chat_id, "Step 4/4: send StringSession")
                            elif step == "string_session":
                                st["string_session"] = text
                                try:
                                    store.save_user(
                                        st["label"],
                                        {
                                            "label": st["label"],
                                            "display_name": st["label"],
                                            "api_id": st["api_id"],
                                            "api_hash": st["api_hash"],
                                            "user_id": 0,
                                            "string_session": st["string_session"],
                                            "active": True,
                                            "settings": {},
                                        },
                                    )
                                    await send_msg(client, chat_id, f"Added account: {st['label']}. Restart bot to activate.", menu=True)
                                except Exception as exc:
                                    await send_msg(client, chat_id, f"Add failed: {exc}")
                                pending_add.pop(chat_id, None)
                            pending_phone.pop(chat_id, None)
                            continue


                        if chat_id in pending_phone:
                            st = pending_phone[chat_id]
                            step = st.get("step")
                            if step == "label":
                                st["label"] = text
                                st["step"] = "api_id"
                                await send_msg(client, chat_id, "Phone wizard 2/6: send api_id")
                            elif step == "api_id":
                                try:
                                    st["api_id"] = int(text)
                                    st["step"] = "api_hash"
                                    await send_msg(client, chat_id, "Phone wizard 3/6: send api_hash")
                                except ValueError:
                                    await send_msg(client, chat_id, "api_id must be integer")
                            elif step == "api_hash":
                                st["api_hash"] = text
                                st["step"] = "phone"
                                await send_msg(client, chat_id, "Phone wizard 4/6: send phone number with +countrycode")
                            elif step == "phone":
                                st["phone"] = text
                                temp = None
                                try:
                                    try:
                                        await send_msg(client, chat_id, "Requesting login code from Telegram... please wait. OTP will come to your Telegram app/SMS.")
                                    except Exception:
                                        pass
                                    temp = TelegramClient(StringSession(), st["api_id"], st["api_hash"])
                                    await temp.connect()
                                    sent = await temp.send_code_request(st["phone"])
                                    st["phone_code_hash"] = sent.phone_code_hash
                                    st["temp"] = temp
                                    st["step"] = "code"
                                    try:
                                        await send_msg(client, chat_id, "Phone wizard 5/6: send login code. Check your official Telegram app/SMS for OTP (it is NOT sent by this bot).")
                                    except Exception:
                                        pass
                                except Exception as exc:
                                    # Sometimes Telegram may still deliver code even if request flow throws.
                                    if st.get("temp") and st.get("phone_code_hash"):
                                        st["step"] = "code"
                                        await send_msg(client, chat_id, f"Code request warning: {exc!r}\nIf OTP arrived in Telegram app/SMS, send it now. If not, resend phone or Cancel.")
                                    else:
                                        try:
                                            if temp:
                                                await temp.disconnect()
                                        except Exception:
                                            pass
                                        st["step"] = "phone"
                                        await send_msg(client, chat_id, f"Failed sending code: {exc!r}\nSend phone number again (with +countrycode) or press Cancel.")
                            elif step == "code":
                                temp = st.get("temp")
                                try:
                                    if not temp:
                                        st["step"] = "phone"
                                        await send_msg(client, chat_id, "Login session was reset. Send phone number again (with +countrycode).")
                                        continue
                                    if not temp.is_connected():
                                        await temp.connect()
                                    lowered = (text or "").strip().lower()
                                    if lowered in {"send code again", "resend", "resend code", "/resend"}:
                                        if st.get("phone_code_hash"):
                                            sent = await temp.resend_code_request(st["phone"], st["phone_code_hash"])
                                        else:
                                            sent = await temp.send_code_request(st["phone"])
                                        st["phone_code_hash"] = sent.phone_code_hash
                                        await send_msg(client, chat_id, "Requested a fresh OTP from Telegram. Send the new code from your Telegram app/SMS.")
                                        st["step"] = "code"
                                        continue
                                    code_value = (text or "").strip().replace(" ", "")
                                    try:
                                        await temp.sign_in(phone=st["phone"], code=code_value)
                                    except (errors.PhoneCodeHashEmptyError, errors.PhoneCodeHashInvalidError):
                                        await temp.sign_in(phone=st["phone"], code=code_value, phone_code_hash=st.get("phone_code_hash"))
                                    me = await temp.get_me()
                                    string_session = temp.session.save()
                                    store.save_user(st["label"], {
                                        "label": st["label"],
                                        "display_name": (me.first_name or st["label"]),
                                        "api_id": st["api_id"],
                                        "api_hash": st["api_hash"],
                                        "user_id": me.id,
                                        "string_session": string_session,
                                        "active": True,
                                        "settings": {},
                                    })
                                    await send_msg(client, chat_id, f"Added account by phone: {st['label']} (restart to activate)", menu=True)
                                    await temp.disconnect()
                                    pending_phone.pop(chat_id, None)
                                except errors.SessionPasswordNeededError:
                                    st["step"] = "password"
                                    await send_msg(client, chat_id, "Phone wizard 6/6: send 2FA password")
                                except Exception as exc:
                                    if isinstance(exc, (errors.PhoneCodeExpiredError, errors.PhoneCodeHashExpiredError)):
                                        try:
                                            if st.get("phone_code_hash"):
                                                sent = await temp.resend_code_request(st["phone"], st["phone_code_hash"])
                                            else:
                                                sent = await temp.send_code_request(st["phone"])
                                            st["phone_code_hash"] = sent.phone_code_hash
                                            await send_msg(client, chat_id, "Your previous OTP expired. I requested a fresh OTP from Telegram.\nSend the new code from your Telegram app/SMS or press Cancel.")
                                        except Exception as resend_exc:
                                            await send_msg(client, chat_id, f"Code expired and auto-resend failed: {resend_exc}\nSend phone number again (with +countrycode) or press Cancel.")
                                            st["step"] = "phone"
                                            continue
                                    elif isinstance(exc, errors.PhoneCodeInvalidError):
                                        await send_msg(client, chat_id, "Invalid OTP. Please send the latest code from your Telegram app/SMS.\nIf needed, type 'resend' for a new code or press Cancel.")
                                    else:
                                        await send_msg(client, chat_id, f"Login failed: {exc}\nSend code again (or type 'resend') or press Cancel.")
                                    st["step"] = "code"
                            elif step == "password":
                                temp = st.get("temp")
                                try:
                                    await temp.sign_in(password=text)
                                    me = await temp.get_me()
                                    string_session = temp.session.save()
                                    store.save_user(st["label"], {
                                        "label": st["label"],
                                        "display_name": (me.first_name or st["label"]),
                                        "api_id": st["api_id"],
                                        "api_hash": st["api_hash"],
                                        "user_id": me.id,
                                        "string_session": string_session,
                                        "active": True,
                                        "settings": {},
                                    })
                                    await send_msg(client, chat_id, f"Added account by phone+2FA: {st['label']} (restart to activate)", menu=True)
                                    await temp.disconnect()
                                except Exception as exc:
                                    await send_msg(client, chat_id, f"2FA failed: {exc}")
                                pending_phone.pop(chat_id, None)
                            continue

                except Exception:
                    await asyncio.sleep(2)

    print("Control bot started (Bot API polling mode).")
    return asyncio.create_task(poll_loop())

async def start_client(label: str, profile: dict):
    client = TelegramClient(StringSession(profile["string_session"]), profile["api_id"], profile["api_hash"])
    await client.start()
    me = await client.get_me()
    logger.info("[online] %s as %s (%s)", label, me.first_name, me.id)
    try:
        d = store.load_user(label)
        d["user_id"] = me.id
        d["display_name"] = me.first_name or d.get("display_name", label)
        store.save_user(label, d)
    except Exception:
        pass
    await register_handlers(client, label)
    asyncio.create_task(story_auto_worker(client, label))
    return client


async def main():
    control_bot = await start_control_bot()
    labels = store.list_users()
    if not labels:
        print("No user accounts found yet. Use control bot /add command or run frontend.py.")
    clients = []
    for label in labels:
        p = store.load_user(label)
        if not p.get("active", True):
            continue
        try:
            clients.append(await start_client(label, p))
        except Exception as exc:
            logger.exception("[startup-error] %s :: %s", label, exc)
    tasks = []
    if clients:
        print(f"Started {len(clients)} userbot client(s). Ctrl+C to stop.")
        tasks.extend([c.run_until_disconnected() for c in clients])
    else:
        print("No active user clients. Control bot can still manage accounts.")
    if control_bot:
        tasks.append(control_bot)
    if tasks:
        await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
