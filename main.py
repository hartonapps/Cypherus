from __future__ import annotations

import asyncio
import re
import time
from collections import defaultdict, deque
from pathlib import Path

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

HELP_TEXT = """**Cypherus Userbot Menu**

Core:
- .ping -> latency check
- .menu / .help -> show all commands
- .logout -> terminate this account session
- .reset -> delete this account profile locally

Automation:
- .autoreply on <text> | .autoreply off
- .autoreact on 😀🔥 | .autoreact off
- .antispam on|off

Media:
- reply + .s -> image to sticker
- reply + .toimg -> sticker to png
- reply + .kang <pack_short_name> 😀

Downloads:
- .dl <url>
- .meta <url>

AI/Tools:
- .gpt <text>
- .ask <question>
- .summarize <text>
- .translate <text> to <lang>
- .qr <text>
- .short <url>
- .calc <expression>

Groups:
- .tagall
- .kick @user
- .promote @user
- .demote @user
- reply/.pin, .unpin
"""


def parse_command(text: str) -> tuple[str, str]:
    raw = text[len(COMMAND_PREFIX) :].strip()
    if not raw:
        return "", ""
    parts = raw.split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""
    return cmd, arg


def is_expiring_or_viewonce(message) -> bool:
    if getattr(message, "ttl_period", None):
        return True
    media = getattr(message, "media", None)
    if not media:
        return False

    # Best effort TTL detection
    ttl = getattr(media, "ttl_seconds", None)
    if ttl:
        return True

    if isinstance(media, types.MessageMediaDocument):
        doc = media.document
        if doc and any(isinstance(a, types.DocumentAttributeVideo) and a.supports_streaming for a in doc.attributes):
            return False
    return False


async def save_media_if_needed(client: TelegramClient, message, label: str) -> None:
    if not message.media:
        return
    if not is_expiring_or_viewonce(message):
        return

    user_media_dir = MEDIA_DIR / label
    user_media_dir.mkdir(parents=True, exist_ok=True)

    try:
        local_path = None
        if SAVE_EXTRACTED_TO_LOCAL:
            local_path = await message.download_media(file=user_media_dir)
        if SAVE_EXTRACTED_TO_SAVED_MESSAGES:
            await client.forward_messages("me", message)
        logger.info("[extract] %s extracted media %s", label, local_path)
    except Exception as exc:
        logger.exception("[extract-error] %s :: %s", label, exc)


async def update_user_settings(label: str, mutator):
    data = store.load_user(label)
    mutator(data)
    store.save_user(label, data)


async def register_handlers(client: TelegramClient, label: str):
    anti_spam_map: dict[int, deque[float]] = defaultdict(deque)

    @client.on(events.NewMessage(incoming=True))
    async def incoming_handler(event):
        msg = event.message
        await save_media_if_needed(client, msg, label)

        data = store.load_user(label)
        settings = data.get("settings", {})

        autoreply = settings.get("autoreply", {})
        if autoreply.get("enabled") and event.is_private and not event.out:
            await event.reply(autoreply.get("text", "I'm currently away."))

        if settings.get("autoreact", {}).get("enabled"):
            emojis = settings["autoreact"].get("emojis", "🔥")
            first = emojis[0]
            try:
                await client(functions.messages.SendReactionRequest(
                    peer=event.chat_id,
                    msg_id=event.message.id,
                    reaction=[types.ReactionEmoji(emoticon=first)],
                    big=False,
                    add_to_recent=True,
                ))
            except Exception:
                pass

        antispam = settings.get("antispam", {})
        if antispam.get("enabled") and event.is_group:
            uid = event.sender_id
            now = time.time()
            dq = anti_spam_map[uid]
            dq.append(now)
            window = antispam.get("window", DEFAULT_ANTISPAM_WINDOW)
            limit = antispam.get("limit", DEFAULT_ANTISPAM_LIMIT)
            while dq and (now - dq[0] > window):
                dq.popleft()
            if len(dq) > limit:
                try:
                    await event.delete()
                except Exception:
                    pass

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\."))
    async def command_handler(event):
        cmd, arg = parse_command(event.raw_text)
        if not cmd:
            return

        try:
            if cmd in {"help", "menu"}:
                await event.edit(HELP_TEXT)

            elif cmd == "ping":
                t0 = time.perf_counter()
                await event.edit("Pinging...")
                ms = (time.perf_counter() - t0) * 1000
                await event.edit(f"🏓 Pong: {ms:.2f}ms")

            elif cmd == "autoreply":
                if arg.startswith("on "):
                    text = arg[3:].strip()
                    if not text:
                        await event.edit("Usage: .autoreply on <text>")
                        return

                    def mutate(d):
                        d["settings"]["autoreply"] = {"enabled": True, "text": text}

                    await update_user_settings(label, mutate)
                    await event.edit("Auto-reply enabled.")
                elif arg.strip() == "off":
                    def mutate(d):
                        d["settings"]["autoreply"]["enabled"] = False

                    await update_user_settings(label, mutate)
                    await event.edit("Auto-reply disabled.")
                else:
                    await event.edit("Usage: .autoreply on <text> | .autoreply off")

            elif cmd == "autoreact":
                if arg.startswith("on "):
                    em = arg[3:].strip() or "🔥"

                    def mutate(d):
                        d["settings"]["autoreact"] = {"enabled": True, "emojis": em}

                    await update_user_settings(label, mutate)
                    await event.edit(f"Auto-react enabled: {em}")
                elif arg.strip() == "off":
                    def mutate(d):
                        d["settings"]["autoreact"]["enabled"] = False

                    await update_user_settings(label, mutate)
                    await event.edit("Auto-react disabled.")
                else:
                    await event.edit("Usage: .autoreact on 😀🔥 | .autoreact off")

            elif cmd == "antispam":
                state = arg.strip().lower()
                if state not in {"on", "off"}:
                    await event.edit("Usage: .antispam on|off")
                    return

                    
                def mutate(d):
                    d["settings"]["antispam"]["enabled"] = state == "on"

                await update_user_settings(label, mutate)
                await event.edit(f"Antispam {state}.")

            elif cmd == "calc":
                if not arg:
                    await event.edit("Usage: .calc <expression>")
                else:
                    result = safe_calc(arg)
                    await event.edit(f"Result: `{result}`")

            elif cmd == "short":
                if not arg:
                    await event.edit("Usage: .short <url>")
                else:
                    s = await shorten_url(arg)
                    await event.edit(s)

            elif cmd == "qr":
                if not arg:
                    await event.edit("Usage: .qr <text>")
                else:
                    png = build_qr_png_bytes(arg)
                    await client.send_file(event.chat_id, png, caption="QR generated")
                    await event.delete()

            elif cmd in {"gpt", "ask"}:
                if not arg:
                    await event.edit(f"Usage: .{cmd} <text>")
                else:
                    out = await ask_free_ai(arg)
                    await event.edit(out[:4000])

            elif cmd == "summarize":
                text = arg or (event.get_reply_message() and (await event.get_reply_message()).raw_text)
                if not text:
                    await event.edit("Usage: .summarize <text> or reply + .summarize")
                else:
                    await event.edit(summarize_text(text))

            elif cmd == "translate":
                m = re.match(r"(.+)\s+to\s+([a-zA-Z-]+)$", arg)
                if not m:
                    await event.edit("Usage: .translate <text> to <language_code>")
                else:
                    txt, lang = m.groups()
                    out = await translate_text(txt, lang)
                    await event.edit(out)

            elif cmd == "dl":
                if not arg:
                    await event.edit("Usage: .dl <url>")
                else:
                    await event.edit("Downloading...")
                    path = await asyncio.to_thread(download_media, arg, MEDIA_DIR / label / "downloads")
                    await client.send_file(event.chat_id, path, caption=f"Downloaded: {path.name}")
                    await event.delete()

            elif cmd == "meta":
                if not arg:
                    await event.edit("Usage: .meta <url>")
                else:
                    data = await asyncio.to_thread(extract_metadata, arg)
                    msg = "\n".join([f"{k}: {v}" for k, v in data.items()])
                    await event.edit(msg[:4000])

            elif cmd == "s":
                reply = await event.get_reply_message()
                if not reply or not reply.media:
                    await event.edit("Reply to an image/sticker with .s")
                    return
                temp_dir = MEDIA_DIR / label / "tmp"
                temp_dir.mkdir(parents=True, exist_ok=True)
                src = Path(await reply.download_media(file=temp_dir / "src"))
                out = image_to_sticker(src, temp_dir / "sticker.webp")
                await client.send_file(event.chat_id, out)
                await event.delete()

            elif cmd == "toimg":
                reply = await event.get_reply_message()
                if not reply or not reply.media:
                    await event.edit("Reply to a sticker with .toimg")
                    return
                temp_dir = MEDIA_DIR / label / "tmp"
                temp_dir.mkdir(parents=True, exist_ok=True)
                src = Path(await reply.download_media(file=temp_dir / "sticker"))
                out = sticker_to_image(src, temp_dir / "sticker.png")
                await client.send_file(event.chat_id, out)
                await event.delete()

            elif cmd == "kang":
                reply = await event.get_reply_message()
                if not reply or not reply.media:
                    await event.edit("Reply to sticker/image: .kang <pack_short_name> 😀")
                    return
                parts = arg.split()
                if len(parts) < 1:
                    await event.edit("Usage: .kang <pack_short_name> 😀")
                    return
                pack = parts[0]
                emoji = parts[1] if len(parts) > 1 else "😀"
                temp_dir = MEDIA_DIR / label / "tmp"
                temp_dir.mkdir(parents=True, exist_ok=True)
                src = Path(await reply.download_media(file=temp_dir / "kang_src"))
                if src.suffix.lower() != ".webp":
                    src = image_to_sticker(src, temp_dir / "kang.webp")
                uploaded = await client.upload_file(src)
                me = await client.get_me()
                doc = await client(functions.messages.UploadMediaRequest(
                    peer="me",
                    media=types.InputMediaUploadedDocument(
                        file=uploaded,
                        mime_type="image/webp",
                        attributes=[types.DocumentAttributeFilename(file_name="sticker.webp")],
                    ),
                ))
                if not isinstance(doc, types.MessageMediaDocument):
                    await event.edit("Failed to prepare sticker document.")
                    return
                await client(functions.stickers.AddStickerToSetRequest(
                    stickerset=types.InputStickerSetShortName(short_name=pack),
                    sticker=types.InputStickerSetItem(
                        document=doc.document,
                        emoji=emoji,
                    ),
                ))
                await event.edit(f"Sticker added to pack `{pack}`")

            elif cmd == "tagall":
                if not event.is_group:
                    await event.edit("Use in groups only.")
                    return
                mentions = []
                async for user in client.iter_participants(event.chat_id):
                    mentions.append(f"[{user.first_name}](tg://user?id={user.id})")
                    if len(mentions) >= 50:
                        break
                await event.edit(" ".join(mentions))

            elif cmd in {"kick", "promote", "demote"}:
                if not event.is_group:
                    await event.edit("Group only command.")
                    return
                target = arg.strip()
                if not target and event.is_reply:
                    rm = await event.get_reply_message()
                    target = rm.sender_id
                if not target:
                    await event.edit(f"Usage: .{cmd} @user or reply")
                    return

                entity = await client.get_input_entity(target)
                if cmd == "kick":
                    await client.kick_participant(event.chat_id, entity)
                elif cmd == "promote":
                    await client.edit_admin(event.chat_id, entity, is_admin=True, manage_call=True, ban_users=True)
                else:
                    await client.edit_admin(event.chat_id, entity, is_admin=False)
                await event.edit(f"{cmd} done.")

            elif cmd == "pin":
                rm = await event.get_reply_message()
                if not rm:
                    await event.edit("Reply to a message and use .pin")
                else:
                    await client.pin_message(event.chat_id, rm.id)
                    await event.delete()

            elif cmd == "unpin":
                await client.unpin_message(event.chat_id)
                await event.delete()

            elif cmd == "logout":
                data = store.load_user(label)
                data["active"] = False
                store.save_user(label, data)
                await event.edit("Logged out: set account inactive. Stop/restart main.py")

            elif cmd == "reset":
                store.delete_user(label)
                await event.edit("Local account profile deleted.")

            else:
                await event.edit("Unknown command. Use .menu")

            logger.info("[cmd] %s -> %s %s", label, cmd, arg)
        except Exception as exc:
            logger.exception("[cmd-error] %s %s :: %s", label, cmd, exc)
            await event.edit(f"Error: {exc}\nUse .menu for command usage.")


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
        profile = store.load_user(label)
        if not profile.get("active", True):
            continue
        try:
            c = await start_client(label, profile)
            clients.append(c)
        except Exception as exc:
            logger.exception("[startup-error] %s :: %s", label, exc)

    if not clients:
        print("No active clients started.")
        return

    print(f"Started {len(clients)} userbot client(s). Press Ctrl+C to stop.")
    await asyncio.gather(*[c.run_until_disconnected() for c in clients])


if __name__ == "__main__":
    asyncio.run(main())
