from __future__ import annotations

import ast
import operator
from io import BytesIO
from urllib.parse import urlparse

import httpx
import qrcode

from config import URL_SHORTENER_ENDPOINT

ALLOWED_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
}


def safe_calc(expr: str) -> float:
    def _eval(node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.BinOp):
            op = ALLOWED_OPS[type(node.op)]
            return op(_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp):
            op = ALLOWED_OPS[type(node.op)]
            return op(_eval(node.operand))
        raise ValueError("Unsupported expression")

    tree = ast.parse(expr, mode="eval")
    return _eval(tree.body)


async def shorten_url(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme:
        raise ValueError("URL must include http:// or https://")

    async with httpx.AsyncClient(timeout=20) as client:
        res = await client.get(URL_SHORTENER_ENDPOINT, params={"format": "simple", "url": url})
        res.raise_for_status()
        return res.text.strip()


def build_qr_png_bytes(text: str) -> bytes:
    img = qrcode.make(text)
    bio = BytesIO()
    img.save(bio, format="PNG")
    return bio.getvalue()
