from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import random


@dataclass
class Order:
    side: str
    entry: float
    sl: float
    tp: float
    lots: float = 0.1
    note: str = ""


@dataclass
class Fill:
    price: float
    slippage_pts: float
    latency_ms: int


def slip_points(spread_pts: float, model: str, fixed_pts: int, k: float) -> float:
    if model == "fixed_pts":
        return max(0.0, abs(random.gauss(fixed_pts, fixed_pts * 0.3)))
    base = spread_pts * k
    return max(0.0, abs(random.gauss(base, base * 0.5)))


def simulate_entry(bar, order: Order, point: float, model: str, fixed_pts: int, k: float, latency_ms: int) -> Fill:
    spread_pts = max(1.0, bar.spr / point) if getattr(bar, "spr", 0) else max(1.0, (bar.h - bar.l) / point * 0.05)
    s = slip_points(spread_pts, model, fixed_pts, k)
    px = order.entry + (s * point if order.side == "BUY" else -s * point)
    return Fill(price=px, slippage_pts=s, latency_ms=latency_ms)


def hit_sequence(o: Order, bar, priority: str) -> Optional[str]:
    if priority == "SL_first":
        if o.side == "BUY":
            if bar.l <= o.sl:
                return "SL"
            if bar.h >= o.tp:
                return "TP"
        else:
            if bar.h >= o.sl:
                return "SL"
            if bar.l <= o.tp:
                return "TP"
    elif priority == "TP_first":
        if o.side == "BUY":
            if bar.h >= o.tp:
                return "TP"
            if bar.l <= o.sl:
                return "SL"
        else:
            if bar.l <= o.tp:
                return "TP"
            if bar.h >= o.sl:
                return "SL"
    else:
        if o.side == "BUY":
            if bar.h >= o.tp:
                return "TP"
            if bar.l <= o.sl:
                return "SL"
        else:
            if bar.l <= o.tp:
                return "TP"
            if bar.h >= o.sl:
                return "SL"
    return None


