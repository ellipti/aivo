import sqlite3, os

DB = os.environ.get("AIVO_DB_PATH", "aivo_trades.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS strategy_perf(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  strategy_id TEXT NOT NULL,
  symbol TEXT NOT NULL,
  closed_at INTEGER NOT NULL,
  r_multiple REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sp_key ON strategy_perf(strategy_id, symbol, closed_at);

CREATE TABLE IF NOT EXISTS ab_assign(
  oid TEXT PRIMARY KEY,
  symbol TEXT, group_id TEXT, strategies TEXT, assigned_at INTEGER
);
"""

if __name__ == "__main__":
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA)
    con.commit()
    con.close()


