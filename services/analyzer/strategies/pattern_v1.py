from __future__ import annotations

from typing import List, Dict, Optional
from .base import StrategyAdapter, StratDecision


class Strategy(StrategyAdapter):
    def next(self, symbol: str, rows: List[Dict]) -> Optional[StratDecision]:
        if len(rows) < 20:
            return None
        # Demo: always WAIT-like unless simple condition
        last = rows[-1]
        prev = rows[-2]
        if last["close"] > prev["close"]:
            entry = last["close"]
            return StratDecision(True, "BUY", entry, entry - 40, entry + 80, 65, "demo_up", "PATTERN_V1")
        return None


