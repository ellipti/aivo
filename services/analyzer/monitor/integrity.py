from __future__ import annotations
from typing import List, Dict, Tuple


def check_ohlcv_gaps(rows: List[Dict], max_gap_bars: int) -> Tuple[bool, str]:
    if len(rows) < 3:
        return (True, "ok")
    gaps = 0
    for i in range(1, len(rows)):
        dt = rows[i]["time"] - rows[i - 1]["time"]
        if dt > (rows[i].get("timeframe_sec") or rows[i - 1].get("timeframe_sec") or 0):
            gaps += 1
    return (gaps <= max_gap_bars, f"gaps={gaps}")


def check_candle_wick_anomaly(rows: List[Dict], max_wick_ratio: float) -> Tuple[bool, str]:
    if not rows:
        return (True, "ok")
    r = rows[-1]
    body = abs(r["close"] - r["open"])
    rng = (r["high"] - r["low"])
    ratio = (rng / max(1e-9, body)) if body > 0 else float("inf")
    return (ratio <= max_wick_ratio, f"wick_ratio={round(ratio, 2)}")


def check_zero_spread(zero_count: int, cap: int) -> Tuple[bool, str]:
    return (zero_count <= cap, f"zero_spread_bars={zero_count}")


