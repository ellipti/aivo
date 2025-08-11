from __future__ import annotations

import os
import json
import hashlib
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

from .logger import info, warn


@dataclass
class Circuit:
    name: str
    fail_threshold: int = 3
    cool_down_sec: int = 120
    fails: int = 0
    opened_at: float = 0.0

    def record_success(self) -> None:
        self.fails = 0
        self.opened_at = 0.0

    def record_fail(self) -> None:
        self.fails += 1
        if self.fails >= self.fail_threshold:
            self.opened_at = time.time()

    def is_open(self) -> bool:
        if self.opened_at == 0.0:
            return False
        if time.time() - self.opened_at >= self.cool_down_sec:
            # half-open
            self.fails = 0
            self.opened_at = 0.0
            return False
        return True


_ID_FILE = "last_order_ids.json"


def _load_ids() -> Dict[str, Any]:
    if not os.path.exists(_ID_FILE):
        return {}
    try:
        with open(_ID_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_ids(d: Dict[str, Any]) -> None:
    with open(_ID_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


def make_order_id(symbol: str, side: str, entry: float, sl: float, tp: float, bucket: str) -> str:
    raw = f"{symbol}|{side}|{entry}|{sl}|{tp}|{bucket}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def is_duplicate_order(order_id: str, ttl_sec: int = 900) -> bool:
    data = _load_ids()
    rec = data.get(order_id)
    now = time.time()
    if rec and now - rec.get("ts", 0) < ttl_sec:
        return True
    data[order_id] = {"ts": now}
    _save_ids(data)
    return False


def chart_is_fresh(path: str, max_age_sec: int = 300) -> bool:
    if not os.path.exists(path):
        return False
    mtime = os.path.getmtime(path)
    return (time.time() - mtime) <= max_age_sec


def degraded_decision(pattern_signals: List[dict], min_score: float = 70.0) -> dict:
    """
    GPT Vision унтарсан үед: зөвхөн A зэрэглэлийн дохио байвал гүйцэтгэх, үгүй бол WAIT.
    pattern_signals: PatternScanner-ын гаргалтын dict (name, direction, confidence, close, time...)
    """
    if not pattern_signals:
        return {"decision": "WAIT", "reason": "No patterns in degraded mode"}

    best = max(pattern_signals, key=lambda s: s.get("confidence", 0))
    if best.get("confidence", 0) >= min_score:
        side = "BUY" if best.get("direction") == "BULL" else "SELL"
        px = float(best.get("close"))
        if side == "BUY":
            entry, sl, tp = px, px - 20.0, px + 40.0
        else:
            entry, sl, tp = px, px + 20.0, px - 40.0
        return {
            "decision": side,
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "reason": f"Degraded mode via {best.get('name')} {best.get('confidence')}",
        }
    return {"decision": "WAIT", "reason": f"Low confidence {best.get('confidence')} in degraded mode"}


