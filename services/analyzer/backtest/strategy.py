from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List, Dict


@dataclass
class Signal:
    side: str
    entry: float
    sl: float
    tp: float
    lots: float
    note: str


class Strategy:
    def __init__(self, rr: float = 2.0, min_stop: float = 10.0):
        self.rr = rr
        self.min_stop = min_stop

    def next(self, bars: List[Dict]) -> Optional[Signal]:
        if len(bars) < 30:
            return None
        last = bars[-1]
        if bars[-2]["close"] < bars[-1]["close"] and bars[-3]["close"] < bars[-2]["close"]:
            px = last["close"]
            sl = px - max(self.min_stop, (last["close"] - last["open"]))
            tp = px + self.rr * (px - sl)
            return Signal("BUY", px, sl, tp, 0.1, "demo-bull2")
        if bars[-2]["close"] > bars[-1]["close"] and bars[-3]["close"] > bars[-2]["close"]:
            px = last["close"]
            sl = px + max(self.min_stop, (last["open"] - last["close"]))
            tp = px - self.rr * (sl - px)
            return Signal("SELL", px, sl, tp, 0.1, "demo-bear2")
        return None


