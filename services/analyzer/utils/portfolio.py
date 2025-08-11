from __future__ import annotations

import sqlite3, os, json, time
from typing import Dict, List, Tuple

DB = os.environ.get("AIVO_DB_PATH", "aivo_trades.db")


def _q(sql, params=()):
    con = sqlite3.connect(DB)
    try:
        cur = con.execute(sql, params)
        return cur.fetchall()
    finally:
        con.close()


def load_pf_cfg(path="configs/portfolio.json"):
    return json.load(open(path, "r", encoding="utf-8"))


def load_symbol_cfg(path="configs/guardrails.json"):
    return json.load(open(path, "r", encoding="utf-8"))["symbol"]


def open_trades() -> List[dict]:
    sql = """
    SELECT t.oid, t.symbol, t.entry, t.sl, t.tp, t.risk_pts, IFNULL(t.volume,0), IFNULL(t.risk_pct_used,0), t.opened_at
    FROM trades t
    LEFT JOIN closes c ON c.oid = t.oid
    WHERE c.id IS NULL
    """
    rows = _q(sql)
    return [
        dict(oid=r[0], symbol=r[1], entry=r[2], sl=r[3], tp=r[4], risk_pts=r[5], volume=r[6], risk_pct=r[7], opened_at=r[8])
        for r in rows
    ]


def per_symbol_open_count() -> Dict[str, int]:
    d: Dict[str, int] = {}
    for r in open_trades():
        d[r["symbol"]] = d.get(r["symbol"], 0) + 1
    return d


def current_risk_pct() -> float:
    return round(sum((r["risk_pct"] or 0.0) for r in open_trades()), 4)


def var_r(symbol: str, lookback: int = 60, confidence: float = 0.95) -> float:
    sql = "SELECT r_multiple FROM closes WHERE oid IN (SELECT oid FROM trades WHERE symbol=?) ORDER BY closed_at DESC LIMIT ?"
    rows = _q(sql, (symbol, lookback))
    rs = [float(x[0]) for x in rows if x[0] is not None]
    if len(rs) < 10:
        return 1.0
    q_idx = max(1, int((1.0 - confidence) * len(rs)))
    rs_sorted = sorted(rs)
    v = rs_sorted[q_idx - 1]
    return abs(v) if v < 0 else 0.5


def decay_flag(symbol: str, lookback=40, min_hit=35.0, min_avg_r=-0.3, cooldown_min=240) -> Tuple[bool, str]:
    rows = _q(
        """SELECT r_multiple, closed_at FROM closes 
                 WHERE oid IN (SELECT oid FROM trades WHERE symbol=?)
                 ORDER BY closed_at DESC LIMIT ?""",
        (symbol, lookback),
    )
    if len(rows) < 12:
        return (False, "insufficient history")
    rs = [float(r[0]) for r in rows]
    hit = 100.0 * sum(1 for r in rs if r > 0) / len(rs)
    avg_r = sum(rs) / len(rs)
    flag = (hit < min_hit) and (avg_r <= min_avg_r)
    marker = f".decay.{symbol}.stamp"
    now = time.time()
    if flag:
        open(marker, "w", encoding="utf-8").write(str(now))
        return (True, f"decay hit: hit={hit:.1f} avgR={avg_r:.2f}")
    if os.path.exists(marker):
        last = float(open(marker, "r", encoding="utf-8").read().strip() or "0")
        if now - last < cooldown_min * 60:
            return (True, f"in cooldown {int((cooldown_min*60 - (now-last))//60)}m")
    return (False, "ok")


def can_open(symbol: str, need_risk_pct: float, pf_cfg: dict) -> Tuple[bool, str]:
    if need_risk_pct > pf_cfg["per_trade_max_pct"]:
        return (False, f"per-trade cap {pf_cfg['per_trade_max_pct']}%")
    ttl = current_risk_pct()
    if ttl + need_risk_pct > pf_cfg["risk_cap_pct"]:
        return (False, f"portfolio risk cap {pf_cfg['risk_cap_pct']}% exceed")
    cnt = per_symbol_open_count().get(symbol, 0)
    if cnt >= pf_cfg["per_symbol_max_concurrent"]:
        return (False, f"{symbol} concurrent >= {pf_cfg['per_symbol_max_concurrent']}")
    dc, why = decay_flag(
        symbol,
        lookback=pf_cfg["decay"]["lookback_trades"],
        min_hit=pf_cfg["decay"]["min_hit_rate_pct"],
        min_avg_r=pf_cfg["decay"]["min_avg_r"],
        cooldown_min=pf_cfg["decay"]["cooldown_minutes"],
    )
    if dc:
        return (False, f"decay/cooldown: {why}")
    return (True, "ok")


def dynamic_risk_pct(symbol: str, base_pct: float, pf_cfg: dict) -> float:
    v = var_r(symbol, pf_cfg["var"]["lookback_trades"], pf_cfg["var"]["confidence"])
    adj = base_pct / (1.0 + max(0.1, v))
    return round(min(adj, pf_cfg["per_trade_max_pct"]), 4)


