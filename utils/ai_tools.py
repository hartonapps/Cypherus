from __future__ import annotations

import re
from collections import Counter

import httpx

AI_ENDPOINT = "https://devtoolbox-api.devtoolbox-api.workers.dev/ai/generate"
FREE_TRANSLATE_ENDPOINT = "https://libretranslate.de/translate"


async def ask_free_ai(prompt: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=35) as client:
            res = await client.post(AI_ENDPOINT, json={"prompt": prompt})
            if res.is_success:
                data = res.json()
                out = data.get("response") or data.get("result") or data.get("text")
                if out:
                    return str(out)
    except Exception:
        pass
    return "AI endpoint unavailable right now. Try again in a bit."


def summarize_text(text: str, max_sentences: int = 3) -> str:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    if len(sentences) <= max_sentences:
        return text.strip()

    words = re.findall(r"\w+", text.lower())
    freq = Counter(w for w in words if len(w) > 2)
    scored = []
    for sent in sentences:
        sent_words = re.findall(r"\w+", sent.lower())
        score = sum(freq.get(w, 0) for w in sent_words) / max(len(sent_words), 1)
        scored.append((score, sent))
    top = sorted(scored, key=lambda x: x[0], reverse=True)[:max_sentences]
    return " ".join(s for _, s in top)


async def translate_text(text: str, target_language: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.post(
                FREE_TRANSLATE_ENDPOINT,
                json={"q": text, "source": "auto", "target": target_language.lower(), "format": "text"},
            )
            if res.is_success:
                data = res.json()
                if data.get("translatedText"):
                    return data["translatedText"]
    except Exception:
        pass
    return "Translation endpoint unavailable. Usage: .translate hello to es"
