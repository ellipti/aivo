from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Optional

from services.analyzer.utils.pattern_scanner import scan_patterns
from services.analyzer.utils.guardrails import (
    load_guardrails,
    detect_regime,
    classify_session,
    min_score_for,
)


@dataclass
class TradePlan:
    side: str  # BUY/SELL
    entry: float
    sl: float
    tp: float
    reason: str
    conf_score: float
    regime: str
    session: str


class AIVOGuardedStrategy:
    """
    Backtest-д conservative logic (GPT-гүй):
      - Pattern score >= regime босго
      - BUY → Hammer, SELL → Bearish Engulfing
      - Entry = close, SL/TP = ±(RR, stop_pts=~ATR)
    """

    def __init__(self, guardrails_path: str = "configs/guardrails.json", rr: float = 2.0, stop_pts_min: float = 10.0):
        self.cfg = load_guardrails(guardrails_path)
        self.rr = rr
        self.stop_pts_min = stop_pts_min

    def propose(self, rows: List[Dict]) -> Optional[TradePlan]:
        if len(rows) < 25:
            return None
        reg = detect_regime(rows, self.cfg)
        session = classify_session(int(rows[-1]["time"]), self.cfg)
        min_score = min_score_for(reg.regime, self.cfg)

        sigs = scan_patterns(rows[-60:])  # сүүлийн 60 лаанд хайна
        if not sigs:
            return None

        top_bull = next((s for s in sigs if s.direction == "BULL"), None)
        top_bear = next((s for s in sigs if s.direction == "BEAR"), None)

        choice = None
        if top_bull and top_bear:
            choice = top_bull if top_bull.confidence >= top_bear.confidence else top_bear
        else:
            choice = top_bull or top_bear

        if not choice:
            return None
        if choice.confidence < min_score:
            return None

        px = float(choice.extras["close"])
        stop_pts = max(self.stop_pts_min, reg.atr_abs or self.stop_pts_min)

        if choice.direction == "BULL":
            entry, sl, tp = px, px - stop_pts, px + self.rr * stop_pts
            side = "BUY"
        else:
            entry, sl, tp = px, px + stop_pts, px - self.rr * stop_pts
            side = "SELL"

        return TradePlan(
            side=side,
            entry=entry,
            sl=sl,
            tp=tp,
            reason=f"{choice.name}@{choice.confidence} Regime={reg.regime}",
            conf_score=choice.confidence,
            regime=reg.regime,
            session=session,
        )


