from dataclasses import dataclass
from typing import Optional, List, Dict


@dataclass
class StratDecision:
    ok: bool
    side: str           # BUY/SELL
    entry: float
    sl: float
    tp: float
    score: float        # 0..100
    reason: str
    strategy_id: str


class StrategyAdapter:
    def next(self, symbol: str, rows: List[Dict]) -> Optional[StratDecision]:
        raise NotImplementedError


