from __future__ import annotations

from pathlib import Path

from PIL import Image


def image_to_sticker(image_path: Path, out_path: Path) -> Path:
    with Image.open(image_path).convert("RGBA") as img:
        img.thumbnail((512, 512))
        canvas = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
        x = (512 - img.width) // 2
        y = (512 - img.height) // 2
        canvas.paste(img, (x, y), img)
        canvas.save(out_path, "WEBP", quality=95)
    return out_path


def sticker_to_image(sticker_path: Path, out_path: Path) -> Path:
    with Image.open(sticker_path) as img:
        img.convert("RGBA").save(out_path, "PNG")
    return out_path
