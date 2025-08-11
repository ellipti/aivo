from __future__ import annotations

import sqlite3, os, time, json
from typing import Any, Dict

DB = os.environ.get("AIVO_DB_PATH", "aivo_trades.db")


def log_trade_open(oid: str, symbol: str, direction: str, entry: float, sl: float, tp: float, strategy: str, timeframe: str, context: Dict[str, Any]):
    opened_at = int(time.time())
    risk_pts = abs(entry - sl)
    rr_target = abs(tp - entry) / max(risk_pts, 1e-9)
    con = sqlite3.connect(DB)
    try:
        con.execute(
            """INSERT OR IGNORE INTO trades(oid, symbol, side, entry, sl, tp, risk_pts, rr_target, opened_at, note, strategy_id)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (oid, symbol, direction, entry, sl, tp, risk_pts, rr_target, opened_at, json.dumps(context, ensure_ascii=False), strategy),
        )
        con.commit()
    finally:
        con.close()


def log_trade_close(oid: str, exit_price: float, exit_reason: str):
    closed_at = int(time.time())
    con = sqlite3.connect(DB)
    try:
        row = con.execute("SELECT entry, sl, tp FROM trades WHERE oid=?", (oid,)).fetchone()
        if not row:
            return False
        entry, sl, tp = row
        pnl_pts = (exit_price - entry)
        side = con.execute("SELECT side FROM trades WHERE oid=?", (oid,)).fetchone()[0]
        if side == "SELL":
            pnl_pts = (entry - exit_price)
        risk_pts = abs(entry - sl)
        r_multiple = pnl_pts / max(risk_pts, 1e-9)
        con.execute(
            """INSERT INTO closes (oid, exit_price, exit_reason, closed_at, pnl_pts, r_multiple)
                        VALUES (?,?,?,?,?,?)""",
            (oid, exit_price, exit_reason, closed_at, pnl_pts, r_multiple),
        )
        con.commit()
        return True
    finally:
        con.close()


