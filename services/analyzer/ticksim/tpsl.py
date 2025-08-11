from __future__ import annotations

from dataclasses import dataclass
from typing import List
from .loader import Tick


@dataclass
class ExitResult:
    exit: str
    exit_px: float
    dur_ms: int


def follow_tpsl(side: str, fill_px: float, sl: float, tp: float, ticks: List[Tick]) -> ExitResult:
    t0 = ticks[0].t if ticks else 0
    for i in range(1, len(ticks)):
        b, a = ticks[i].bid, ticks[i].ask
        if side == "BUY":
            if b >= tp:
                return ExitResult("TP", tp, ticks[i].t - t0)
            if a <= sl:
                return ExitResult("SL", sl, ticks[i].t - t0)
        else:
            if a <= tp:
                return ExitResult("TP", tp, ticks[i].t - t0)
            if b >= sl:
                return ExitResult("SL", sl, ticks[i].t - t0)
    return ExitResult("NONE", fill_px, (ticks[-1].t - t0) if ticks else 0)


