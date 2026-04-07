from __future__ import annotations

import re
from collections import Counter

import httpx

from config import FREE_AI_ENDPOINTS, FREE_TRANSLATE_ENDPOINT


async def ask_free_ai(prompt: str) -> str:
    # Endpoint 1 (best effort): DevToolbox-style public endpoint.
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.post(FREE_AI_ENDPOINTS[0], json={"prompt": prompt})
            if res.is_success:
                data = res.json()
                out = data.get("response") or data.get("text") or data.get("result")
                if out:
                    return str(out)
    except Exception:
        pass

    # Endpoint 2: DuckDuckGo instant answer API.
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.get(
                FREE_AI_ENDPOINTS[1],
                params={"q": prompt, "format": "json", "no_redirect": 1, "no_html": 1},
            )
            if res.is_success:
                data = res.json()
                answer = data.get("AbstractText") or data.get("Answer")
                if answer:
                    return answer
    except Exception:
        pass

    return (
        "I couldn't reach a free AI endpoint right now. "
        "Try again later, or use .summarize / .translate which can work locally."
    )


def summarize_text(text: str, max_sentences: int = 3) -> str:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    if len(sentences) <= max_sentences:
        return text.strip()

    words = re.findall(r"\w+", text.lower())
    freq = Counter(w for w in words if len(w) > 2)

    scored: list[tuple[float, str]] = []
    for sent in sentences:
        sent_words = re.findall(r"\w+", sent.lower())
        score = sum(freq.get(w, 0) for w in sent_words) / max(len(sent_words), 1)
        scored.append((score, sent))

    top = sorted(scored, key=lambda x: x[0], reverse=True)[:max_sentences]
    return " ".join([s for _, s in top])


async def translate_text(text: str, target_language: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            res = await client.post(
                FREE_TRANSLATE_ENDPOINT,
                json={
                    "q": text,
                    "source": "auto",
                    "target": target_language.lower(),
                    "format": "text",
                },
            )
            if res.is_success:
                data = res.json()
                translated = data.get("translatedText")
                if translated:
                    return translated
    except Exception:
        pass
    return "Translation endpoint unavailable. Example usage: .translate hello to es"
