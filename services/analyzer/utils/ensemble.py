from __future__ import annotations

import json
from typing import List, Dict, Tuple

from ..strategies.base import StratDecision


def load_ens(path: str = "configs/ensemble.json"):
    return json.load(open(path, "r", encoding="utf-8"))


_perf_ema: dict[tuple[str, str], float] = {}


def _ema(key, r, alpha=0.5):
    prev = _perf_ema.get(key)
    val = alpha * r + (1 - alpha) * (prev if prev is not None else 0.0)
    _perf_ema[key] = val
    return val


def update_perf_ema(strategy_id: str, symbol: str, r_multiple: float, alpha=0.5):
    return _ema((strategy_id, symbol), r_multiple, alpha)


def blend_scores(decisions: List[StratDecision], symbol: str, ens_cfg: dict) -> StratDecision | None:
    if not decisions:
        return None
    sides = [d.side for d in decisions]
    side: str
    if ens_cfg["blend"]["direction_conflict_policy"] == "majority":
        side = max(set(sides), key=sides.count)
        decisions = [d for d in decisions if d.side == side]
    else:
        decisions.sort(key=lambda d: d.score, reverse=True)
        side = decisions[0].side

    sa = float(ens_cfg["blend"]["score_alpha"])  # score weight
    pa = float(ens_cfg["blend"]["perf_alpha"])   # performance EMA weight
    mx = max(1.0, max(d.score for d in decisions))
    items: List[tuple[float, StratDecision]] = []
    for d in decisions:
        key = (d.strategy_id, symbol)
        perf = _perf_ema.get(key, 0.0)
        w = sa * (d.score / mx) + pa * max(-1.0, min(1.0, (perf / 3.0)))
        items.append((w, d))
    items.sort(key=lambda x: x[0], reverse=True)
    return items[0][1] if items else None


