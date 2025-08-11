from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime

from .strategies.aivo_guarded import AIVOGuardedStrategy, TradePlan


@dataclass
class Candle:
    t: int
    o: float
    h: float
    l: float
    c: float
    v: float


def _parse_row(r: Dict) -> Candle:
    def _time(x):
        s = str(x)
        if s.isdigit():
            return int(s)
        return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())

    return Candle(
        t=_time(r["time"]),
        o=float(r["open"]),
        h=float(r["high"]),
        l=float(r["low"]),
        c=float(r["close"]),
        v=float(r.get("tick_volume", r.get("volume", 0))),
    )


def load_csv(path: str) -> List[Candle]:
    out: List[Candle] = []
    with open(path, "r", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out.append(_parse_row(r))
    return out


def row_dict(c: Candle) -> Dict:
    return {"time": c.t, "open": c.o, "high": c.h, "low": c.l, "close": c.c, "tick_volume": c.v}


@dataclass
class BtConfig:
    walk_train_bars: int = 2000
    walk_test_bars: int = 500
    rr: float = 2.0
    min_stop_pts: float = 10.0
    max_concurrent: int = 1


@dataclass
class Position:
    side: str
    entry: float
    sl: float
    tp: float
    open_idx: int
    oid: str


def simulate_walk_forward(candles: List[Candle], cfg: BtConfig, strat: AIVOGuardedStrategy):
    i = cfg.walk_train_bars
    equity_r = 0.0
    stats: List[Dict] = []
    open_pos: Optional[Position] = None

    def oid(i: int, side: str, entry: float, sl: float, tp: float) -> str:
        return f"{i}-{side}-{round(entry,2)}-{round(sl,2)}-{round(tp,2)}"

    while i < len(candles):
        window_start = max(0, i - cfg.walk_train_bars)
        test_end = min(len(candles), i + cfg.walk_test_bars)
        test = candles[i:test_end]

        for j in range(len(test)):
            idx = i + j
            hist = candles[: idx + 1]
            rows = [row_dict(x) for x in hist]

            if open_pos is None:
                plan = strat.propose(rows)
                if plan:
                    open_pos = Position(
                        side=plan.side,
                        entry=plan.entry,
                        sl=plan.sl,
                        tp=plan.tp,
                        open_idx=idx,
                        oid=oid(idx, plan.side, plan.entry, plan.sl, plan.tp),
                    )

            if open_pos:
                c = candles[idx]
                if open_pos.side == "BUY":
                    if c.l <= open_pos.sl:
                        r = (open_pos.sl - open_pos.entry) / abs(open_pos.entry - open_pos.sl)
                        equity_r += r
                        stats.append({"oid": open_pos.oid, "exit": "SL", "r": r, "ts": c.t})
                        open_pos = None
                    elif c.h >= open_pos.tp:
                        r = (open_pos.tp - open_pos.entry) / abs(open_pos.entry - open_pos.sl)
                        equity_r += r
                        stats.append({"oid": open_pos.oid, "exit": "TP", "r": r, "ts": c.t})
                        open_pos = None
                else:
                    if c.h >= open_pos.sl:
                        r = (open_pos.entry - open_pos.sl) / abs(open_pos.entry - open_pos.sl)
                        equity_r += r
                        stats.append({"oid": open_pos.oid, "exit": "SL", "r": r, "ts": c.t})
                        open_pos = None
                    elif c.l <= open_pos.tp:
                        r = (open_pos.entry - open_pos.tp) / abs(open_pos.entry - open_pos.sl)
                        equity_r += r
                        stats.append({"oid": open_pos.oid, "exit": "TP", "r": r, "ts": c.t})
                        open_pos = None

        i += cfg.walk_test_bars

    closed = len(stats)
    wins = sum(1 for s in stats if s["r"] > 0)
    hit = (wins / closed * 100) if closed else 0.0
    avg_r = sum(s["r"] for s in stats) / closed if closed else 0.0
    cum_r = sum(s["r"] for s in stats)

    return {
        "closed_trades": closed,
        "wins": wins,
        "hit_rate_pct": round(hit, 2),
        "avg_r": round(avg_r, 3),
        "cum_r": round(cum_r, 3),
        "stats": stats,
    }


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="Path to OHLCV csv")
    ap.add_argument("--train", type=int, default=2000)
    ap.add_argument("--test", type=int, default=500)
    ap.add_argument("--rr", type=float, default=2.0)
    ap.add_argument("--minstop", type=float, default=10.0)
    ap.add_argument("--guardrails", default="configs/guardrails.json")
    ap.add_argument("--out", default="bt_result.json")
    args = ap.parse_args()

    candles = load_csv(args.csv)
    strat = AIVOGuardedStrategy(guardrails_path=args.guardrails, rr=args.rr, stop_pts_min=args.minstop)
    cfg = BtConfig(walk_train_bars=args.train, walk_test_bars=args.test, rr=args.rr, min_stop_pts=args.minstop)
    res = simulate_walk_forward(candles, cfg, strat)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(f"Saved: {args.out}")


