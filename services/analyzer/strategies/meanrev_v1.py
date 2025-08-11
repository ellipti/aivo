from __future__ import annotations

from typing import List, Dict, Optional
from .base import StrategyAdapter, StratDecision


class Strategy(StrategyAdapter):
    def next(self, symbol: str, rows: List[Dict]) -> Optional[StratDecision]:
        if len(rows) < 25:
            return None
        closes = [r["close"] for r in rows[-20:]]
        avg = sum(closes) / len(closes)
        last = rows[-1]
        if last["close"] < avg * 0.997:
            e = last["close"]
            return StratDecision(True, "BUY", e, e - 35, e + 60, 58, "demo_meanrev_buy", "MEANREV_V1")
        if last["close"] > avg * 1.003:
            e = last["close"]
            return StratDecision(True, "SELL", e, e + 35, e - 60, 58, "demo_meanrev_sell", "MEANREV_V1")
        return None


