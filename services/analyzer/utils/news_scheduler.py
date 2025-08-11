from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import List, Dict, Tuple
import json


def load_sched(path: str = "configs/scheduler.json"):
    return json.load(open(path, "r", encoding="utf-8"))


def in_session(now_utc: datetime, sess_cfg: dict) -> str:
    h = now_utc.hour
    lo = sess_cfg["LONDON"]
    ny = sess_cfg["NY"]
    asia = sess_cfg["ASIA"]
    if lo[0] <= h <= lo[1]:
        return "LONDON"
    if ny[0] <= h <= ny[1]:
        return "NY"
    if h >= asia[0] or h <= asia[1]:
        return "ASIA"
    return "OTHER"


def news_blackout(
    now_utc: datetime, symbol: str, events: List[Dict], before: int = 30, after: int = 30
) -> Tuple[bool, str]:
    for ev in events or []:
        if symbol.upper() not in [s.upper() for s in ev.get("symbols", [])]:
            continue
        t = datetime.fromisoformat(str(ev["time_utc"]).replace("Z", "+00:00"))
        if t - timedelta(minutes=before) <= now_utc <= t + timedelta(minutes=after):
            return True, f"news blackout: {ev.get('title', 'news')}"
    return False, ""


