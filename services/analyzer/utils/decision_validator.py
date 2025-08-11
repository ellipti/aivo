from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Optional, Dict, Any

ALLOWED_DECISIONS = {"BUY", "SELL", "WAIT"}


@dataclass
class Decision:
    decision: str
    entry: Optional[float]
    sl: Optional[float]
    tp: Optional[float]
    reason: str


class DecisionError(Exception):
    pass


def _try_json(text: str) -> Optional[Dict[str, Any]]:
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None


def _try_regex(text: str) -> Optional[Dict[str, Any]]:
    # Flexible fallback: Decision/Entry/StopLoss/TakeProfit anywhere
    result: Dict[str, Any] = {}
    m = re.search(r"Decision\s*:\s*(BUY|SELL|WAIT)", text, re.I)
    if m:
        result["Decision"] = m.group(1).upper()
    for key in ("Entry", "StopLoss", "TakeProfit"):
        m = re.search(rf"{key}\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)", text, re.I)
        if m:
            result[key] = float(m.group(1))
    m = re.search(r"Reason\s*:\s*(.+)", text, re.I)
    if m:
        result["Reason"] = m.group(1).strip()
    return result if result else None


def parse_gpt(text: str) -> Decision:
    data = _try_json(text) or _try_regex(text)
    if not data:
        raise DecisionError("GPT output parse failed")

    dec = str(data.get("Decision", "")).upper()
    if dec not in ALLOWED_DECISIONS:
        raise DecisionError(f"Invalid Decision: {dec}")

    entry = float(data.get("Entry")) if data.get("Entry") is not None else None
    sl = float(data.get("StopLoss")) if data.get("StopLoss") is not None else None
    tp = float(data.get("TakeProfit")) if data.get("TakeProfit") is not None else None
    reason = str(data.get("Reason") or "").strip()

    return Decision(decision=dec, entry=entry, sl=sl, tp=tp, reason=reason)


def validate(
    dec: Decision,
    *,
    symbol: str = "XAUUSD",
    min_rr: float = 1.2,
    min_distance_pts: float = 10.0,
) -> Decision:
    """
    Policy filters:
    - WAIT is OK (no entry)
    - BUY/SELL must include Entry/SL/TP
    - RR >= min_rr
    - Entry↔SL/TP distances >= min_distance_pts
    - Basic price sanity by symbol
    """
    if dec.decision == "WAIT":
        return dec

    for name, value in (("Entry", dec.entry), ("StopLoss", dec.sl), ("TakeProfit", dec.tp)):
        if value is None:
            raise DecisionError(f"Missing {name}")

    # Geometry and RR
    if dec.decision == "BUY":
        if not (dec.sl < dec.entry < dec.tp):
            raise DecisionError("BUY geometry invalid (SL < Entry < TP)")
        risk = dec.entry - dec.sl
        reward = dec.tp - dec.entry
        rr = reward / risk if risk > 0 else 0.0
        if risk < min_distance_pts or reward < min_distance_pts:
            raise DecisionError("BUY distances too tight")
    else:  # SELL
        if not (dec.tp < dec.entry < dec.sl):
            raise DecisionError("SELL geometry invalid (TP < Entry < SL)")
        risk = dec.sl - dec.entry
        reward = dec.entry - dec.tp
        rr = reward / risk if risk > 0 else 0.0
        if risk < min_distance_pts or reward < min_distance_pts:
            raise DecisionError("SELL distances too tight")

    if rr < min_rr:
        raise DecisionError(f"RR too low: {rr:.2f} < {min_rr}")

    # Sanity range by symbol (example: XAUUSD)
    if symbol.upper() == "XAUUSD":
        for v in (dec.entry, dec.sl, dec.tp):
            if v is None or not (500 <= v <= 5000):
                raise DecisionError("Out-of-range price for XAUUSD")

    return dec


