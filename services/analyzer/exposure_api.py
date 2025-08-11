from fastapi import APIRouter
import sqlite3, os, json
from typing import Dict, List

DB = os.environ.get("AIVO_DB_PATH", "aivo_trades.db")
CFG = json.load(open("configs/dashboard.json", "r", encoding="utf-8"))
router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _q(sql, params=()):
    con = sqlite3.connect(DB)
    cur = con.execute(sql, params)
    rows = cur.fetchall()
    con.close()
    return rows


def open_trades():
    sql = """
    SELECT t.oid, t.symbol, IFNULL(t.strategy_id,'NA'), IFNULL(t.risk_pct_used,0), IFNULL(t.volume,0), t.entry, t.sl, t.tp
    FROM trades t
    LEFT JOIN closes c ON c.oid=t.oid
    WHERE c.id IS NULL
    """
    rows = _q(sql)
    out = []
    for r in rows:
        out.append(
            dict(
                oid=r[0],
                symbol=r[1],
                strategy=r[2] or "NA",
                risk_pct=float(r[3] or 0.0),
                volume=float(r[4] or 0.0),
                entry=float(r[5] or 0.0),
                sl=float(r[6] or 0.0),
                tp=float(r[7] or 0.0),
            )
        )
    return out


@router.get("/exposure")
def exposure_snapshot():
    ots = open_trades()
    by_symbol: Dict[str, float] = {}
    by_strategy: Dict[str, float] = {}
    ttl = 0.0
    for t in ots:
        ttl += t["risk_pct"]
        by_symbol[t["symbol"]] = by_symbol.get(t["symbol"], 0.0) + t["risk_pct"]
        by_strategy[t["strategy"]] = by_strategy.get(t["strategy"], 0.0) + t["risk_pct"]
    cap = CFG["risk_caps"]["portfolio_pct"]
    return {
        "open_trades": len(ots),
        "portfolio_risk_pct": round(ttl, 4),
        "portfolio_cap_pct": cap,
        "by_symbol": {k: round(v, 4) for k, v in by_symbol.items()},
        "by_strategy": {k: round(v, 4) for k, v in by_strategy.items()},
    }


def _risk_cell(symbol: str, strategy: str, trades: List[dict]) -> float:
    return sum(t["risk_pct"] for t in trades if t["symbol"] == symbol and t["strategy"] == strategy)


@router.get("/heatmap")
def heatmap():
    cfgH = CFG["heatmap"]
    rows = cfgH["rows"]
    cols = cfgH["cols"]
    ots = open_trades()
    cap = float(CFG["risk_caps"]["portfolio_pct"]) or 1.0
    matrix = []
    for r in rows:
        row = []
        for c in cols:
            v = _risk_cell(r, c, ots)
            row.append(round(v / cap, 4))
        matrix.append(row)
    return {
        "rows": rows,
        "cols": cols,
        "matrix": matrix,
        "warn": cfgH["warn_pct"],
        "alert": cfgH["alert_pct"],
        "portfolio_cap_pct": cap,
    }


