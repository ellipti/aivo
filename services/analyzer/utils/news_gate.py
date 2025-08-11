from __future__ import annotations

from typing import List, Dict, Tuple
from datetime import datetime, timezone, timedelta


def in_blackout(now_utc: datetime, symbol: str, events: List[Dict], cfg: dict) -> Tuple[bool, str]:
    """
    events: [{ "time_utc": "2025-08-11T08:30:00Z", "impact": "High", "symbols": ["XAUUSD","USD"], "title": "CPI" }, ...]
    """
    nb = cfg["news"]
    if symbol.upper() not in [s.upper() for s in nb["apply_to"]]:
        return (False, "symbol not in scope")

    before = timedelta(minutes=int(nb["blackout_minutes_before"]))
    after = timedelta(minutes=int(nb["blackout_minutes_after"]))
    impacts = set(nb["impact_levels"])

    for ev in events or []:
        if ev.get("impact") not in impacts:
            continue
        t = ev.get("time_utc")
        if not t:
            continue
        ev_time = datetime.fromisoformat(str(t).replace("Z", "+00:00"))
        if (ev_time - before) <= now_utc <= (ev_time + after):
            return (True, f"blackout around {ev.get('title', 'news')}")

    return (False, "no blackout")


