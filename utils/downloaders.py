from __future__ import annotations

from pathlib import Path

import yt_dlp


def download_media(url: str, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    template = str(out_dir / "%(title).80s_%(id)s.%(ext)s")
    ydl_opts = {
        "outtmpl": template,
        "noplaylist": True,
        "quiet": True,
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
    return Path(filename)


def extract_metadata(url: str) -> dict:
    with yt_dlp.YoutubeDL({"quiet": True, "noplaylist": True}) as ydl:
        info = ydl.extract_info(url, download=False)
    return {
        "title": info.get("title"),
        "uploader": info.get("uploader"),
        "duration": info.get("duration"),
        "view_count": info.get("view_count"),
        "webpage_url": info.get("webpage_url"),
        "description": (info.get("description") or "")[:500],
    }
