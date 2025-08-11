from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Optional
import statistics as stats
from datetime import datetime, timezone


@dataclass
class Candle:
    time: int  # epoch seconds
    open: float
    high: float
    low: float
    close: float
    tick_volume: float = 0.0

    @property
    def body(self) -> float:
        return abs(self.close - self.open)

    @property
    def upper_shadow(self) -> float:
        return self.high - max(self.open, self.close)

    @property
    def lower_shadow(self) -> float:
        return min(self.open, self.close) - self.low

    @property
    def is_bull(self) -> bool:
        return self.close >= self.open

    @property
    def is_bear(self) -> bool:
        return self.close < self.open


def to_candles(rows: List[Dict]) -> List[Candle]:
    out: List[Candle] = []
    for r in rows:
        out.append(
            Candle(
                time=int(r.get("time") or r.get("Time") or r.get("timestamp")),
                open=float(r["open"]),
                high=float(r["high"]),
                low=float(r["low"]),
                close=float(r["close"]),
                tick_volume=float(r.get("tick_volume", r.get("volume", 0.0))),
            )
        )
    return out


# -----------------------
# Pattern detectors
# -----------------------


def is_hammer(
    c: Candle,
    *,
    body_max_ratio: float = 0.4,
    lower_to_body_min: float = 2.0,
    upper_to_body_max: float = 0.3,
) -> bool:
    """
    Bullish Hammer (доод сүүдэр том, дээд сүүдэр бага, бие жижиг)
    - body <= body_max_ratio * (high-low)
    - lower_shadow >= lower_to_body_min * body
    - upper_shadow <= upper_to_body_max * body
    """
    rng = max(c.high - c.low, 1e-9)
    if c.body > body_max_ratio * rng:
        return False
    if c.lower_shadow < lower_to_body_min * c.body:
        return False
    if c.upper_shadow > upper_to_body_max * c.body:
        return False
    return True


def is_bearish_engulf(curr: Candle, prev: Candle, *, min_body_factor: float = 0.6) -> bool:
    """
    Bearish Engulfing:
    - prev нь өссөн лаа, curr буурсан лаа
    - curr body нь prev body-г бүхэлд нь 'багтаах' (open>=prev.close, close<=prev.open)
    - curr body хангалттай том
    """
    if not (prev.is_bull and curr.is_bear):
        return False
    prev_body = prev.body
    curr_body = curr.body
    if curr.open < prev.close or curr.close > prev.open:
        return False
    if curr_body < min_body_factor * (prev_body + 1e-9):
        return False
    return True


# -----------------------
# Indicators (lightweight)
# -----------------------


def sma(values: List[float], period: int) -> Optional[float]:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def atr(candles: List[Candle], period: int = 14) -> Optional[float]:
    if len(candles) < period + 1:
        return None
    trs: List[float] = []
    for i in range(1, len(candles)):
        h = candles[i].high
        l = candles[i].low
        pc = candles[i - 1].close
        tr = max(h - l, abs(h - pc), abs(l - pc))
        trs.append(tr)
    if len(trs) < period:
        return None
    return sum(trs[-period:]) / period


# -----------------------
# Session / context helpers
# -----------------------


def session_weight(ts_epoch: int, tz: timezone = timezone.utc) -> float:
    """
    Лондон/Нью-Йорк-д илүү жин өгнө.
    - Лондон (UTC 7–16) → 1.0
    - Нью-Йорк (UTC 12–21) → 1.0
    - Азид (UTC 23–7) → 0.7
    - бусад → 0.85
    """
    h = datetime.fromtimestamp(ts_epoch, tz=tz).hour
    if 7 <= h <= 16:  # London
        return 1.0
    if 12 <= h <= 21:  # NY (давхардах 12–16 зүгээр)
        return 1.0
    if h >= 23 or h <= 7:  # Asia
        return 0.7
    return 0.85


def trend_bias(candles: List[Candle], lookback: int = 20) -> float:
    """
    Энгийн чиг хандлага: SMA(lookback) ба түүний налуу.
    - эерэг бол up, сөрөг бол down.
    Буцаах: -1..+1 орчим нормчилсон.
    """
    if len(candles) < lookback + 2:
        return 0.0
    closes = [c.close for c in candles]
    sma_now = sma(closes, lookback)
    sma_prev = sma(closes[:-1], lookback)
    if sma_now is None or sma_prev is None:
        return 0.0
    slope = (sma_now - sma_prev) / max(1e-9, sma_prev)
    return max(-1.0, min(1.0, slope * 20))


def volume_spike(candles: List[Candle], k: float = 1.4, lb: int = 20) -> bool:
    if len(candles) < lb + 1:
        return False
    vols = [c.tick_volume for c in candles[-(lb + 1) : -1]]
    base = (stats.mean(vols) if vols else 0.0) or 1e-9
    return candles[-1].tick_volume > k * base


# -----------------------
# Confirmation score
# -----------------------


@dataclass
class PatternSignal:
    name: str  # "Hammer" | "Bearish Engulfing"
    index: int  # candles[] index
    direction: str  # "BULL" | "BEAR"
    confidence: float  # 0..100
    extras: Dict


def score_confirmation(candles: List[Candle], idx: int, *, direction: str) -> float:
    """
    0..100 оноо.
    Бүрэлдэхүүн:
      - Session weight (max 20)
      - Trend alignment (max 30)
      - Volume spike (max 20)
      - ATR sanity (max 15)
      - Round-level proximity (max 15)
    """
    c = candles[idx]
    sess = session_weight(c.time)
    sess_score = 20.0 * sess

    tb = trend_bias(candles[: idx + 1], lookback=20)
    align = tb if direction == "BULL" else -tb
    trend_score = 30.0 * max(0.0, (align + 1.0) / 2.0)

    vol_boost = 20.0 if volume_spike(candles[: idx + 1], k=1.4, lb=20) else 8.0

    _atr = atr(candles[: idx + 1], period=14)
    if _atr is None or _atr <= 0:
        atr_score = 8.0
    else:
        rng = candles[idx].high - candles[idx].low
        ratio = rng / _atr
        atr_score = 15.0 if 0.6 <= ratio <= 2.5 else 8.0

    price = c.close
    near_50 = min(abs((price % 100) - 50), abs((price % 50)))
    lvl_score = 15.0 if near_50 <= 2.0 else (10.0 if near_50 <= 5.0 else 5.0)

    return round(min(100.0, sess_score + trend_score + vol_boost + atr_score + lvl_score), 2)


def scan_patterns(rows: List[Dict]) -> List[PatternSignal]:
    """
    Оролт: MT5/CSV-ийн лааны мөрүүд (dict)
    Гаралт: илэрсэн хэлбэрүүд (анхны чансаагаар эрэмбэлээгүй)
    """
    candles = to_candles(rows)
    sigs: List[PatternSignal] = []

    for i in range(1, len(candles)):
        c = candles[i]
        p = candles[i - 1]

        if is_hammer(c):
            conf = score_confirmation(candles, i, direction="BULL")
            sigs.append(
                PatternSignal(
                    name="Hammer",
                    index=i,
                    direction="BULL",
                    confidence=conf,
                    extras={"time": c.time, "close": c.close},
                )
            )

        if is_bearish_engulf(c, p):
            conf = score_confirmation(candles, i, direction="BEAR")
            sigs.append(
                PatternSignal(
                    name="Bearish Engulfing",
                    index=i,
                    direction="BEAR",
                    confidence=conf,
                    extras={"time": c.time, "close": c.close},
                )
            )

    sigs.sort(key=lambda s: s.confidence, reverse=True)
    return sigs


