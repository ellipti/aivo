import sqlite3, os

DB = os.environ.get("AIVO_DB_PATH", "aivo_trades.db")

SC = """
CREATE TABLE IF NOT EXISTS incidents(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 oid TEXT UNIQUE,
 symbol TEXT, strategy_id TEXT,
 opened_at INTEGER, closed_at INTEGER,
 pnl_r REAL, pnl_points REAL,
 verdict TEXT, factors_json TEXT, actions_json TEXT, created_at INTEGER
);
CREATE INDEX IF NOT EXISTS idx_inc_sym ON incidents(symbol, created_at);
"""

if __name__ == "__main__":
    con = sqlite3.connect(DB)
    con.executescript(SC)
    con.commit()
    con.close()


