from __future__ import annotations

import json, os, sqlite3
from typing import Dict, List

DB = os.environ.get("AIVO_DB_PATH", "aivo_trades.db")
CFG = json.load(open("configs/hedge.json", "r", encoding="utf-8"))


def _q(sql, p=()):
    con = sqlite3.connect(DB)
    try:
        cur = con.execute(sql, p)
        return cur.fetchall()
    finally:
        con.close()


def open_trades() -> List[Dict]:
    rows = _q(
        """
        SELECT t.symbol, t.side, IFNULL(t.volume,0), t.entry, t.sl
        FROM trades t LEFT JOIN closes c ON c.oid = t.oid
        WHERE c.id IS NULL
        """
    )
    out: List[Dict] = []
    for r in rows:
        out.append({"symbol": r[0], "side": r[1], "volume": float(r[2] or 0.0), "entry": float(r[3] or 0.0), "sl": float(r[4] or 0.0)})
    return out


def portfolio_risk_pct() -> float:
    rows = _q("SELECT IFNULL(risk_pct_used,0) FROM trades t LEFT JOIN closes c ON c.oid=t.oid WHERE c.id IS NULL")
    return round(sum(float(x[0] or 0.0) for x in rows), 4)


def need_deleveraging() -> bool:
    cap = float(CFG.get("portfolio_cap_pct", 2.0))
    return portfolio_risk_pct() > cap


