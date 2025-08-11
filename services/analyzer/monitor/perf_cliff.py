from __future__ import annotations
from typing import List, Tuple


def check_perf_cliff(last_trades_r: List[float], min_hit: float, min_avg_r: float, dd_r: float) -> Tuple[bool, str]:
    n = len(last_trades_r)
    if n == 0:
        return (True, "no_data")
    hit = 100.0 * sum(1 for x in last_trades_r if x > 0) / n
    avg = sum(last_trades_r) / n
    cum = sum(last_trades_r)
    flag = (hit < min_hit) and (avg <= min_avg_r or cum <= dd_r)
    return (not flag, f"n={n}, hit={round(hit,1)}%, avgR={round(avg,3)}, cumR={round(cum,2)}")


