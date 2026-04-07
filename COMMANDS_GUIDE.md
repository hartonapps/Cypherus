# Cypherus Commands (Simple Explanations)

## Core
- `.menu` / `.help` : Show all commands.
- `.ping` : Check bot speed (latency).
- `.logout` : Disable current account from auto-start.
- `.reset` : Remove local account profile/session.

## Automation
- `.away <text>` : Auto-reply in private chats with your custom AFK text.
- `.away off` : Disable AFK.
- `.schedule <10m|HH:MM> <message>` : Send message later.
- `.filter <word> <response>` : If someone sends that word, bot auto replies.

## Privacy / Logging
- `.ghostmode on|off` : Toggle stealth mode flag.
- `.anti-delete on|off` : If enabled, deleted message text is logged to Saved Messages.
- `.anti-edit on|off` : If enabled, edited messages are logged (old and new text).
- `.hideonline on|off` : Toggle hide-online flag.

## View-Once / Expiring
- `.vvwatch on|off` : Real-time watch and auto-save expiring/view-once media.
- Reply media + `.vvsave` : Force save replied media to Saved Messages.
- Best effort 👀 reaction listener is also included.

## Media tools
- Reply image + `.s` : Convert image to sticker.
- Reply sticker + `.toimg` : Convert sticker to image.
- Reply media + `.compress` : Compress and resend.
- Reply media + `.rename <newname>` : Rename and resend.
- Reply video/gif + `.tomp4` : Convert to MP4.
- Reply image + `.ocr` : Extract text from image.

## Downloads
- `.dl <url>` : Download single media URL.
- `.playlist <url>` : Download playlist.
- `.song <name>` : Search and download first matching song.
- `.meta <url>` : Show media metadata.

## AI / Utility
- `.gpt <text>` / `.ask <text>` : Ask AI endpoint.
- `.summarize <text>` : Summarize text.
- `.translate <text> to <lang>` : Translate text.
- `.qr <text>` : Generate QR image.
- `.short <url>` : Shorten URL.
- `.calc <math>` : Calculator.

## Group admin
- `.tagall` : Mention users.
- `.kick @user` : Remove user.
- `.promote @user` : Promote to admin.
- `.demote @user` : Demote admin.
- `.warn @user` : Add warning (auto-kick at 3).
- `.mute @user 10m` : Temporary mute.
- `.join <invite_link>` : Join via invite.
- Reply message + `.pin` : Pin it.
- `.unpin` : Unpin current pinned message.
