from __future__ import annotations

from typing import List, Dict
import json


CFG = json.load(open("configs/intermarket.json", "r", encoding="utf-8"))


def ema(x: List[float], n: int) -> List[float]:
    if not x:
        return []
    a = 2 / (n + 1)
    y = [x[0]]
    for i in range(1, len(x)):
        y.append(a * x[i] + (1 - a) * y[-1])
    return y


def atr_like(high: List[float], low: List[float], close: List[float], n: int = 14) -> List[float]:
    tr = []
    prev = close[0] if close else 0.0
    for h, l, c in zip(high, low, close):
        tr.append(max(h - l, abs(h - prev), abs(l - prev)))
        prev = c
    return ema(tr, n)


def detect_regime(close: List[float], high: List[float], low: List[float]) -> str:
    if len(close) < 30:
        return "UNKNOWN"
    atr_v = atr_like(high, low, close, 14)
    atr_ratio = (atr_v[-1] / (sum(atr_v[-14:]) / 14.0)) if len(atr_v) >= 14 else 1.0
    if atr_ratio > CFG["regime"]["atr_ratio_high"]:
        return "HIGH_VOL"
    if atr_ratio < CFG["regime"]["atr_ratio_low"]:
        return "LOW_VOL"
    ma20 = sum(close[-20:]) / 20.0
    if close[-1] > ma20:
        return "UP_TREND"
    if close[-1] < ma20:
        return "DOWN_TREND"
    return "RANGE"


