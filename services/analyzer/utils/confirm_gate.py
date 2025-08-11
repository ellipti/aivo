from __future__ import annotations

from typing import List, Dict
from dataclasses import dataclass
from .pattern_scanner import scan_patterns, PatternSignal


@dataclass
class ConfirmationResult:
    ok: bool
    score: float
    reason: str
    top_signals: List[PatternSignal]


def confirm_decision_with_patterns(
    ohlcv_rows: List[Dict],
    *,
    side: str,  # "BUY" | "SELL" | "WAIT"
    min_score: float = 60.0,
    use_top_k: int = 3,
) -> ConfirmationResult:
    """
    GPT шийдвэрийг лааны хэлбэрийн 'баталгаажуулалт'-аар шүүнэ.
    - BUY → bullish дохио (Hammer) оноо бодолцоно
    - SELL → bearish дохио (Bearish Engulfing) оноо бодолцоно
    """
    if side == "WAIT":
        return ConfirmationResult(ok=True, score=0.0, reason="WAIT passthrough", top_signals=[])

    sigs = scan_patterns(ohlcv_rows)
    if not sigs:
        return ConfirmationResult(ok=False, score=0.0, reason="No patterns found", top_signals=[])

    want = "BULL" if side == "BUY" else "BEAR"
    rel = [s for s in sigs if s.direction == want]
    if not rel:
        return ConfirmationResult(
            ok=False, score=0.0, reason="No directional confirmation", top_signals=sigs[:use_top_k]
        )

    rel.sort(key=lambda s: s.confidence, reverse=True)
    best = rel[0]
    avg = sum(s.confidence for s in rel[:use_top_k]) / min(use_top_k, len(rel))

    score = round(0.6 * best.confidence + 0.4 * avg, 2)
    if score >= min_score:
        return ConfirmationResult(
            ok=True,
            score=score,
            reason=f"Confirmed by {best.name} ({best.confidence})",
            top_signals=rel[:use_top_k],
        )

    return ConfirmationResult(
        ok=False, score=score, reason=f"Score {score} < {min_score}", top_signals=rel[:use_top_k]
    )


