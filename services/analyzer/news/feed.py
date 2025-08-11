from __future__ import annotations

import os, json, datetime as dt
from typing import List, Dict
import httpx


CFG = json.load(open("configs/news.json", "r", encoding="utf-8"))
API_BASE = CFG.get("api_base")
API_KEY = os.getenv("TRADINGECONOMICS_KEY", "")


def map_symbols(country: str) -> List[str]:
    return CFG.get("country_map", {}).get(country, [])


def fetch_events() -> List[dict]:
    params = {"c": API_KEY, "f": "json"}
    with httpx.Client(timeout=30) as client:
        r = client.get(API_BASE, params=params)
        r.raise_for_status()
        data = r.json()
    events: List[dict] = []
    for e in data:
        try:
            if str(e.get("importance")) != "3":
                continue
            country = e.get("country")
            when = e.get("date") or e.get("DateTime") or e.get("dateNextRelease")
            events.append({
                "country": country,
                "title": e.get("event") or e.get("Event"),
                "time": when,
                "symbols": map_symbols(country),
            })
        except Exception:
            continue
    return events


def pre_news_pause(symbol: str, now: dt.datetime) -> dict:
    pre_min = int(CFG.get("pre_pause_min", 15))
    for e in fetch_events():
        if symbol in e.get("symbols", []):
            try:
                t = dt.datetime.fromisoformat(str(e.get("time")).replace("Z", "+00:00"))
                if 0 <= (t - now).total_seconds() <= pre_min * 60:
                    return {"pause": True, "reason": f"High impact news: {e.get('title')}"}
            except Exception:
                continue
    return {"pause": False}


