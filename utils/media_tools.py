from __future__ import annotations

import subprocess
from pathlib import Path


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def image_to_sticker(image_path: Path, out_path: Path) -> Path:
    # Lightweight conversion using ffmpeg (available in Termux package).
    _run([
        "ffmpeg",
        "-y",
        "-i",
        str(image_path),
        "-vf",
        "scale=512:512:force_original_aspect_ratio=decrease,pad=512:512:(ow-iw)/2:(oh-ih)/2:color=0x00000000",
        str(out_path),
    ])
    return out_path


def sticker_to_image(sticker_path: Path, out_path: Path) -> Path:
    _run(["ffmpeg", "-y", "-i", str(sticker_path), str(out_path)])
    return out_path
