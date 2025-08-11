from __future__ import annotations

import json, csv
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from .data_loader import load_m1_csv, Bar
from .execution import Order, simulate_entry, hit_sequence
from .strategy import Strategy


@dataclass
class TradeLog:
    oid: str
    side: str
    entry: float
    sl: float
    tp: float
    lots: float
    fill: float
    slip_pts: float
    open_t: int
    close_t: int
    exit: str
    pnl_pts: float
    r: float
    note: str


def run_backtest(cfg: dict) -> Dict[str, Any]:
    bars = load_m1_csv(cfg["data"]["path"])
    sym = cfg["symbol"]
    point = 0.1 if sym.upper() == "XAUUSD" else 0.0001
    strat = Strategy()

    engine = cfg["engine"]
    tpsl = cfg["tp_sl"]

    logs: List[TradeLog] = []
    open_pos: Optional[TradeLog] = None

    events: List[str] = []

    def emit(ev):
        events.append(json.dumps(ev, ensure_ascii=False))

    hist: List[Dict] = []
    for b in bars:
        hist.append({"time": b.t, "open": b.o, "high": b.h, "low": b.l, "close": b.c, "volume": b.v})
        if open_pos:
            ev = hit_sequence(Order(open_pos.side, open_pos.entry, open_pos.sl, open_pos.tp), b, tpsl["priority"])
            if ev:
                if open_pos.side == "BUY":
                    exit_px = open_pos.tp if ev == "TP" else open_pos.sl
                    pnl_pts = exit_px - open_pos.fill
                    r = pnl_pts / max(abs(open_pos.entry - open_pos.sl), 1e-9)
                else:
                    exit_px = open_pos.tp if ev == "TP" else open_pos.sl
                    pnl_pts = open_pos.fill - exit_px
                    r = pnl_pts / max(abs(open_pos.entry - open_pos.sl), 1e-9)
                open_pos.exit = ev
                open_pos.close_t = b.t
                open_pos.pnl_pts = pnl_pts
                open_pos.r = r
                logs.append(open_pos)
                emit({"t": b.t, "type": "close", "exit": ev, "pnl_pts": round(pnl_pts, 2), "r": round(r, 3), "oid": open_pos.oid})
                open_pos = None

        if not open_pos:
            sig = strat.next(hist)
            if sig and sig.side in ("BUY", "SELL"):
                fill = simulate_entry(
                    b,
                    Order(sig.side, sig.entry, sig.sl, sig.tp, sig.lots, sig.note),
                    point,
                    engine["slippage_model"],
                    engine["slippage_fixed_pts"],
                    engine["slippage_k"],
                    engine["latency_ms"],
                )
                oid = f"{b.t}-{sig.side}-{round(sig.entry,2)}"
                tl = TradeLog(
                    oid=oid,
                    side=sig.side,
                    entry=sig.entry,
                    sl=sig.sl,
                    tp=sig.tp,
                    lots=sig.lots,
                    fill=fill.price,
                    slip_pts=fill.slippage_pts,
                    open_t=b.t,
                    close_t=0,
                    exit="",
                    pnl_pts=0.0,
                    r=0.0,
                    note=sig.note,
                )
                open_pos = tl
                emit({"t": b.t, "type": "open", "side": sig.side, "entry": sig.entry, "fill": round(fill.price, 3), "slip_pts": round(fill.slippage_pts, 2), "oid": oid})

    with open(cfg["out"]["trades_csv"], "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow("oid,side,entry,sl,tp,lots,fill,slip_pts,open_t,close_t,exit,pnl_pts,r,note".split(","))
        for x in logs:
            w.writerow(
                [
                    x.oid,
                    x.side,
                    round(x.entry, 3),
                    round(x.sl, 3),
                    round(x.tp, 3),
                    x.lots,
                    round(x.fill, 3),
                    round(x.slip_pts, 2),
                    x.open_t,
                    x.close_t,
                    x.exit,
                    round(x.pnl_pts, 2),
                    round(x.r, 3),
                    x.note,
                ]
            )

    closed = len([x for x in logs if x.exit])
    wins = sum(1 for x in logs if x.r > 0)
    hit = round(100.0 * wins / max(1, closed), 2)
    avg_r = round(sum(x.r for x in logs) / max(1, closed), 3)
    cum_r = round(sum(x.r for x in logs), 3)
    stats = {"closed_trades": closed, "hit_rate_pct": hit, "avg_r": avg_r, "cum_r": cum_r}

    with open(cfg["out"]["stats_json"], "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    with open(cfg["out"]["events_jsonl"], "w", encoding="utf-8") as f:
        f.write("\n".join(events))

    return stats


