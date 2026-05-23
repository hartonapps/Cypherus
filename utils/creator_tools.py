from __future__ import annotations

import io
from pathlib import Path
from urllib.parse import quote_plus, urlparse

import httpx
import markdown2
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def _default_font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", size=size)
    except Exception:
        return ImageFont.load_default()


def make_meme_image(src: Path, top: str, bottom: str, out: Path) -> Path:
    img = Image.open(src).convert("RGB")
    draw = ImageDraw.Draw(img)
    font_size = max(24, img.width // 12)
    font = _default_font(font_size)
    stroke = max(2, font_size // 14)
    draw.text((img.width // 2, 20), top.upper(), fill="white", font=font, anchor="ma", stroke_width=stroke, stroke_fill="black")
    draw.text((img.width // 2, img.height - 20), bottom.upper(), fill="white", font=font, anchor="md", stroke_width=stroke, stroke_fill="black")
    img.save(out, format="JPEG", quality=95)
    return out


def make_text_meme(text: str, out: Path) -> Path:
    img = Image.new("RGB", (1080, 1080), color=(15, 15, 15))
    draw = ImageDraw.Draw(img)
    font = _default_font(56)
    draw.multiline_text((540, 540), text, fill="white", font=font, anchor="mm", align="center", spacing=12)
    img.save(out, format="JPEG", quality=95)
    return out


async def fetch_web_screenshot(url: str, mode: str = "mobile", full: bool = False) -> bytes:
    parsed = urlparse(url)
    if not parsed.scheme:
        url = f"https://{url}"
    base = "https://image.thum.io/get"
    tokens = []
    if full:
        tokens.append("fullpage")
    if mode == "mobile":
        tokens.append("width/430")
    elif mode == "tablet":
        tokens.append("width/820")
    else:
        tokens.append("width/1366")
    shot_url = f"{base}/{'/'.join(tokens)}/{url}"
    async with httpx.AsyncClient(timeout=45, follow_redirects=True) as c:
        r = await c.get(shot_url)
        r.raise_for_status()
        return r.content


def text_to_pdf(title: str, text: str, out: Path) -> Path:
    c = canvas.Canvas(str(out), pagesize=A4)
    w, h = A4
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, h - 50, title)
    c.setFont("Helvetica", 11)
    y = h - 80
    plain = markdown2.markdown(text)
    plain = plain.replace("<p>", "").replace("</p>", "\n").replace("<br />", "\n")
    for line in plain.splitlines():
        if y < 60:
            c.setFont("Helvetica", 9)
            c.drawRightString(w - 40, 30, f"Page {c.getPageNumber()}")
            c.showPage()
            c.setFont("Helvetica", 11)
            y = h - 50
        c.drawString(40, y, line[:120])
        y -= 16
    c.setFont("Helvetica", 9)
    c.drawRightString(w - 40, 30, f"Page {c.getPageNumber()}")
    c.save()
    return out
