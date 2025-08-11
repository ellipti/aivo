from __future__ import annotations

import os, json
import httpx

CFG = json.load(open("configs/news.json", "r", encoding="utf-8"))
MODEL = os.getenv("OPENAI_MODEL") or os.getenv("MODEL") or "gpt-5-thinking"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


def analyze_text(text: str) -> dict:
    if not CFG.get("sentiment", {}).get("enabled", False) or not OPENAI_API_KEY:
        return {"label": "neutral", "score": 0.0}
    prompt = f"Classify this news text into positive/negative/neutral for trading; return JSON with label and score (0..1):\n{text}"
    url = "https://api.openai.com/v1/responses"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": MODEL, "input": prompt, "temperature": 0.0, "max_output_tokens": 200}
    with httpx.Client(timeout=30) as client:
        r = client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()
    text_out = data.get("output_text") or ""
    try:
        return json.loads(text_out)
    except Exception:
        return {"label": "neutral", "score": 0.0}


