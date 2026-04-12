from __future__ import annotations

import asyncio
import os
import re
from collections import Counter

import httpx

AI_ENDPOINT = "https://devtoolbox-api.devtoolbox-api.workers.dev/ai/generate"
FREE_TRANSLATE_ENDPOINT = "https://libretranslate.de/translate"
AI_HORDE_ASYNC_ENDPOINT = "https://aihorde.net/api/v2/generate/async"
AI_HORDE_STATUS_ENDPOINT = "https://aihorde.net/api/v2/generate/status/{job_id}"


async def ask_free_ai(prompt: str, persona: str = "default", memory: list[str] | None = None) -> str:
    memory_text = "\n".join(memory[-6:]) if memory else ""
    full_prompt = (
        f"Persona: {persona}. Keep response concise and useful.\n"
        f"Recent memory:\n{memory_text}\n\n"
        f"User: {prompt}"
    )
    try:
        async with httpx.AsyncClient(timeout=35) as client:
            res = await client.post(AI_ENDPOINT, json={"prompt": full_prompt})
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


async def generate_horde_image(prompt: str, width: int = 512, height: int = 512, steps: int = 20) -> str:
    headers = {"Client-Agent": "Cypherus/1.0"}
    api_key = os.getenv("AI_HORDE_API_KEY")
    if api_key:
        headers["apikey"] = api_key

    try:
        async with httpx.AsyncClient(timeout=45) as client:
            create = await client.post(
                AI_HORDE_ASYNC_ENDPOINT,
                json={"prompt": prompt, "params": {"width": width, "height": height, "steps": steps}},
                headers=headers,
            )
            if not create.is_success:
                return f"Image request failed: HTTP {create.status_code}"
            job_id = (create.json() or {}).get("id")
            if not job_id:
                return "Image request failed: missing job id."

            for _ in range(40):
                await asyncio.sleep(3)
                status = await client.get(AI_HORDE_STATUS_ENDPOINT.format(job_id=job_id), headers=headers)
                if not status.is_success:
                    continue
                data = status.json() or {}
                if data.get("done"):
                    generations = data.get("generations") or []
                    if generations and generations[0].get("img"):
                        return generations[0]["img"]
                    return "Image generation completed, but no image URL was returned."
            return "Image generation timed out. Try again with a shorter prompt."
    except Exception as exc:
        return f"Image generation error: {exc}"
