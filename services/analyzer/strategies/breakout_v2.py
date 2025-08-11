from __future__ import annotations

from typing import List, Dict, Optional
from .base import StrategyAdapter, StratDecision


class Strategy(StrategyAdapter):
    def next(self, symbol: str, rows: List[Dict]) -> Optional[StratDecision]:
        if len(rows) < 30:
            return None
        highs = [r["high"] for r in rows[-20:]]
        lows = [r["low"] for r in rows[-20:]]
        last = rows[-1]
        if last["close"] >= max(highs):
            e = last["close"]
            return StratDecision(True, "BUY", e, e - 45, e + 70, 60, "demo_breakout_up", "BREAKOUT_V2")
        if last["close"] <= min(lows):
            e = last["close"]
            return StratDecision(True, "SELL", e, e + 45, e - 70, 60, "demo_breakout_dn", "BREAKOUT_V2")
        return None


