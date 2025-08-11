from __future__ import annotations

import json, os
from typing import List, Dict, Tuple

from ..intermarket.correlation import evaluate as eval_corr


CFG = json.load(open("configs/hedge.json", "r", encoding="utf-8"))


def find_hedge_pair(symbol: str) -> Tuple[str | None, float]:
    m = CFG.get("hedge_pairs", {}).get(symbol, {})
    if not m:
        return (None, 0.0)
    factor = float(m.get("factor", 0.5))
    return (str(m.get("pair")), factor)


def recommend_hedges(price_close_map: Dict[str, List[float]], open_positions: List[Dict]) -> List[Dict]:
    """Return list of hedge orders to place with fields: symbol, side, lots"""
    corr = eval_corr(price_close_map)
    out: List[Dict] = []
    for pos in open_positions:
        sym = pos["symbol"]
        pair, factor = find_hedge_pair(sym)
        if not pair:
            continue
        key1 = f"{sym}/{pair}"
        key2 = f"{pair}/{sym}"
        score = corr.get(key1) or corr.get(key2)
        if score is None or abs(score) < float(CFG.get("corr_threshold", 0.6)):
            continue
        hedge_symbol = pair
        hedge_side = ("SELL" if pos["side"] == "BUY" else "BUY")
        hedge_lots = round(float(pos.get("volume", 0.01)) * factor, 2)
        if hedge_lots <= 0:
            continue
        out.append({"symbol": hedge_symbol, "side": hedge_side, "volume": hedge_lots})
    return out


