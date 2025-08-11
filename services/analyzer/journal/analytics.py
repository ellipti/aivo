from __future__ import annotations

import sqlite3, os, time, csv
from typing import Dict, Any, List

DB = os.environ.get("AIVO_DB_PATH", "aivo_trades.db")


def _q(sql, params=()):
    con = sqlite3.connect(DB)
    try:
        cur = con.execute(sql, params)
        return cur.fetchall()
    finally:
        con.close()


def kpis(last_days: int | None = None) -> Dict[str, Any]:
    cond = ""
    params: List[Any] = []
    if last_days is not None:
        since = int(time.time()) - last_days * 86400
        cond = " WHERE c.closed_at >= ?"
        params = [since]
    rows = _q(
        f"""
        SELECT c.r_multiple FROM closes c
        {cond}
        """,
        params,
    )
    rs = [float(r[0]) for r in rows]
    n = len(rs)
    hit = (100.0 * sum(1 for x in rs if x > 0) / n) if n else 0.0
    pf = (
        (sum(x for x in rs if x > 0) / abs(sum(x for x in rs if x < 0)))
        if sum(x for x in rs if x < 0) < 0
        else 0.0
    )
    mdd = 0.0
    eq = 0.0
    peak = 0.0
    for r in rs:
        eq += r
        peak = max(peak, eq)
        mdd = max(mdd, peak - eq)
    return {"trades": n, "win_rate": hit, "profit_factor": round(pf, 3), "max_dd_r": round(mdd, 2)}


def by_strategy() -> List[Dict[str, Any]]:
    rows = _q(
        """
        SELECT t.strategy_id, COUNT(c.id), AVG(c.r_multiple)
        FROM trades t
        JOIN closes c ON c.oid = t.oid
        GROUP BY t.strategy_id
        """
    )
    return [
        {"strategy": r[0] or "NA", "trades": int(r[1] or 0), "avg_r": round(float(r[2] or 0.0), 3)} for r in rows
    ]


def export_csv(path: str):
    rows = _q(
        """
        SELECT t.oid, t.symbol, t.side, t.entry, t.sl, t.tp, t.opened_at, IFNULL(t.strategy_id,'NA'), IFNULL(t.note,''),
               c.exit_price, c.exit_reason, c.closed_at, c.pnl_pts, c.r_multiple
        FROM trades t LEFT JOIN closes c ON c.oid = t.oid
        ORDER BY t.opened_at DESC
        """
    )
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "oid",
                "symbol",
                "side",
                "entry",
                "sl",
                "tp",
                "opened_at",
                "strategy",
                "context",
                "exit_price",
                "exit_reason",
                "closed_at",
                "pnl_pts",
                "r_multiple",
            ]
        )
        for r in rows:
            w.writerow(list(r))


