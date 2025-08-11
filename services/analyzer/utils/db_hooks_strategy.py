from __future__ import annotations

import sqlite3, os
from .db import _conn as _dbconn


def log_strategy_perf(oid: str, strategy_id: str, symbol: str, r_multiple: float, closed_at: int):
    with _dbconn() as con:
        con.execute(
            """INSERT INTO strategy_perf(strategy_id,symbol,closed_at,r_multiple)
                       VALUES (?,?,?,?)""",
            (strategy_id, symbol, closed_at, r_multiple),
        )


