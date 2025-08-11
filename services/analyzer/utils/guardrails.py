from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List
from datetime import datetime, timezone
import json
import math

from .pattern_scanner import atr, Candle, to_candles, session_weight


@dataclass
class RegimeResult:
    regime: str  # LOW | NORMAL | HIGH
    atr_abs: float
    atr_ratio: float  # ATR / price


def load_guardrails(path: str = "configs/guardrails.json") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def detect_regime(rows: List[Dict], cfg: dict) -> RegimeResult:
    candles = to_candles(rows)
    _atr = atr(candles, period=cfg["regimes"]["atr_period"]) or 0.0
    price = candles[-1].close if candles else 0.0
    ratio = (_atr / price) if price else 0.0
    low_t = cfg["regimes"]["low_threshold"]
    high_t = cfg["regimes"]["high_threshold"]
    if ratio < low_t:
        r = "LOW"
    elif ratio > high_t:
        r = "HIGH"
    else:
        r = "NORMAL"
    return RegimeResult(regime=r, atr_abs=_atr, atr_ratio=ratio)


def classify_session(ts_epoch: int, cfg: dict) -> str:
    h = datetime.fromtimestamp(ts_epoch, tz=timezone.utc).hour
    lo = cfg["session"]["london_hours_utc"]
    ny = cfg["session"]["ny_hours_utc"]
    asia = cfg["session"]["asia_hours_utc"]
    if lo[0] <= h <= lo[1]:
        return "LONDON"
    if ny[0] <= h <= ny[1]:
        return "NY"
    if h >= asia[0] or h <= asia[1]:
        return "ASIA"
    return "OTHER"


def effective_risk_pct(base_pct: float, regime: str, session: str, cfg: dict) -> float:
    rm = float(cfg["regimes"]["risk_multipliers"][regime])
    sb = float(cfg["session"]["risk_boost"].get(session, 1.0))
    return round(max(0.1, base_pct * rm * sb), 4)


def min_score_for(regime: str, cfg: dict) -> float:
    return float(cfg["regimes"]["min_score_by_regime"][regime])


def clamp_stop_distance(stop_pts: float, cfg: dict) -> float:
    mn = float(cfg["risk"]["min_stop_pts"])
    mx = float(cfg["risk"]["max_stop_pts"])
    return max(mn, min(mx, stop_pts))


def calc_position_size(symbol: str, balance: float, risk_pct: float, entry: float, sl: float, cfg: dict) -> float:
    sym = cfg["symbol"].get(symbol.upper())
    if not sym:
        return 0.01
    contract = float(sym["contract_size"])  # noqa: F841 - kept for future broker-specific calc
    point = float(sym["point"])  # noqa: F841
    point_val = float(sym["point_value"])
    min_lot = float(sym["min_lot"])
    step = float(sym["lot_step"])

    stop_pts = abs(entry - sl)
    stop_pts = clamp_stop_distance(stop_pts, cfg)
    risk_amount = balance * (risk_pct / 100.0)

    loss_per_lot = (stop_pts / max(point, 1e-9)) * point_val
    if loss_per_lot <= 0:
        return min_lot

    lots = risk_amount / loss_per_lot
    lots = max(min_lot, math.floor(lots / step) * step)
    return round(lots, 2)


