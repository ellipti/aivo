from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List, Dict, Tuple

from .pattern_scanner import atr, to_candles


@dataclass
class Regime:
    vol: str  # LOW|MID|HIGH
    liq: str  # LOW|MID|HIGH
    atr_ratio_pct: float
    spread_pts: float


def load_cfg(path: str = "configs/risk_regimes.json") -> dict:
    return json.load(open(path, "r", encoding="utf-8"))


def detect_regime(m1_rows: List[Dict], last_tick: Dict[str, float], point: float, cfg: dict, symbol: str) -> Regime:
    cds = to_candles(m1_rows)
    price = cds[-1].close if cds else 0.0
    _atr = atr(cds, period=14) or 0.0
    atr_ratio_pct = (100.0 * _atr / price) if price else 0.0

    vth = cfg["volatility_pct_threshold"]
    if atr_ratio_pct < float(vth["low"]):
        vol = "LOW"
    elif atr_ratio_pct < float(vth["high"]):
        vol = "MID"
    else:
        vol = "HIGH"

    spread_pts = abs((last_tick.get("ask", 0.0) - last_tick.get("bid", 0.0)) / max(point, 1e-9))
    spc = cfg["liquidity_spread_pts"].get(symbol.upper(), cfg["liquidity_spread_pts"]["default"])
    if spread_pts < float(spc["high"]):
        liq = "HIGH"
    elif spread_pts < float(spc["mid"]):
        liq = "MID"
    else:
        liq = "LOW"

    return Regime(vol=vol, liq=liq, atr_ratio_pct=atr_ratio_pct, spread_pts=spread_pts)


def select_profile(regime: Regime, mapping: dict) -> dict:
    key = f"{regime.vol}_{regime.liq}"
    return mapping.get(key, mapping.get("MID_HIGH", {"rr": 2.0, "tp_pts": 80, "sl_pts": 40, "lot_mult": 1.0}))


def adjust_tp_sl_rr(entry: float, side: str, point: float, profile: dict) -> Tuple[float, float, float]:
    rr = float(profile.get("rr", 1.5))
    tp_pts = float(profile.get("tp_pts", 60))
    sl_pts = float(profile.get("sl_pts", 40))
    tp = entry + (tp_pts * point) * (1 if side == "BUY" else -1)
    sl = entry - (sl_pts * point) * (1 if side == "BUY" else -1)
    return tp, sl, rr


