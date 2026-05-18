from __future__ import annotations

import ast
import operator
from urllib.parse import quote_plus, urlparse

import httpx

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


async def build_qr_png_bytes(text: str) -> bytes:
    # Free endpoint: QR image generation without local heavy dependencies.
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=512x512&data={quote_plus(text)}"
    async with httpx.AsyncClient(timeout=20) as client:
        res = await client.get(qr_url)
        res.raise_for_status()
        return res.content
