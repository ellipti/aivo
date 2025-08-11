from __future__ import annotations

import json
from typing import List, Dict, Tuple


CFG = json.load(open("configs/sizing.json", "r", encoding="utf-8"))


def ema(x: List[float], n: int) -> List[float]:
    if not x:
        return []
    a = 2 / (n + 1)
    y = [x[0]]
    for i in range(1, len(x)):
        y.append(a * x[i] + (1 - a) * y[-1])
    return y


def atr_like(high: List[float], low: List[float], close: List[float], n: int = 14) -> float:
    tr = []
    prev = close[0] if close else 0.0
    for h, l, c in zip(high, low, close):
        tr.append(max(h - l, abs(h - prev), abs(l - prev)))
        prev = c
    at = ema(tr, n)
    return float(at[-1] if at else 0.0)


def calc_lot_size(account_balance: float, risk_percent: float, entry: float, sl: float, point: float, point_value: float, min_lot: float, max_lot: float) -> float:
    risk_amount = account_balance * (risk_percent / 100.0)
    sl_pts = abs(entry - sl) / max(point, 1e-9)
    loss_per_lot = sl_pts * point_value
    if loss_per_lot <= 0:
        return min_lot
    lots = risk_amount / loss_per_lot
    return float(max(min_lot, min(max_lot, round(lots, 2))))


def dynamic_sl_and_lot(symbol: str, side: str, entry: float, account_balance: float, point: float, point_value: float, high: List[float], low: List[float], close: List[float]) -> Tuple[float, float]:
    atr = atr_like(high, low, close, 14)
    sl_off = CFG.get("atr_multiplier", 2.0) * atr
    sl = entry - sl_off if side == "BUY" else entry + sl_off
    lots = calc_lot_size(account_balance, CFG.get("base_risk_pct", 1.0), entry, sl, point, point_value, CFG.get("min_lot", 0.01), CFG.get("max_lot", 5.0))
    return sl, lots


