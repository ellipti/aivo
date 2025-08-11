import sqlite3, os, time
from contextlib import contextmanager

DB_PATH = os.environ.get("AIVO_DB_PATH", "aivo_trades.db")

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS trades (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  oid TEXT UNIQUE,
  symbol TEXT NOT NULL,
  side TEXT CHECK(side IN ('BUY','SELL')) NOT NULL,
  entry REAL NOT NULL,
  sl REAL NOT NULL,
  tp REAL NOT NULL,
  risk_pts REAL NOT NULL,
  rr_target REAL NOT NULL,
  opened_at INTEGER NOT NULL,
  note TEXT
);
CREATE TABLE IF NOT EXISTS closes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  oid TEXT NOT NULL,
  exit_price REAL NOT NULL,
  exit_reason TEXT CHECK(exit_reason IN ('TP','SL','MANUAL')) NOT NULL,
  closed_at INTEGER NOT NULL,
  pnl_pts REAL NOT NULL,
  r_multiple REAL NOT NULL,
  FOREIGN KEY(oid) REFERENCES trades(oid)
);
CREATE INDEX IF NOT EXISTS idx_trades_oid ON trades(oid);
CREATE INDEX IF NOT EXISTS idx_closes_oid ON closes(oid);
"""

@contextmanager
def _conn():
  con = sqlite3.connect(DB_PATH)
  try:
    yield con
    con.commit()
  finally:
    con.close()

def init_db():
  with _conn() as con:
    con.executescript(SCHEMA)

def record_open(oid, symbol, side, entry, sl, tp, note=""):
  opened_at = int(time.time())
  risk_pts = abs(entry - sl)
  rr_target = abs(tp - entry) / max(risk_pts, 1e-9)
  with _conn() as con:
    con.execute("""INSERT OR IGNORE INTO trades
      (oid, symbol, side, entry, sl, tp, risk_pts, rr_target, opened_at, note)
      VALUES (?,?,?,?,?,?,?,?,?,?)""",
      (oid, symbol, side, entry, sl, tp, risk_pts, rr_target, opened_at, note))

def record_close(oid, exit_price, exit_reason):
  closed_at = int(time.time())
  with _conn() as con:
    row = con.execute("SELECT entry, sl, tp FROM trades WHERE oid=?", (oid,)).fetchone()
    if not row: return False
    entry, sl, tp = row
    pnl_pts = (exit_price - entry)
    side = con.execute("SELECT side FROM trades WHERE oid=?", (oid,)).fetchone()[0]
    if side == "SELL": pnl_pts = (entry - exit_price)
    risk_pts = abs(entry - sl)
    r_multiple = pnl_pts / max(risk_pts, 1e-9)
    con.execute("""INSERT INTO closes (oid, exit_price, exit_reason, closed_at, pnl_pts, r_multiple)
                   VALUES (?,?,?,?,?,?)""",
                (oid, exit_price, exit_reason, closed_at, pnl_pts, r_multiple))
    return True


