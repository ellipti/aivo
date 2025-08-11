import sqlite3, os

DB_PATH = os.environ.get("AIVO_DB_PATH", "aivo_trades.db")


def migrate():
  con = sqlite3.connect(DB_PATH)
  cur = con.cursor()

  def _has(col, table):
    cur.execute(f"PRAGMA table_info({table})")
    return any(r[1] == col for r in cur.fetchall())

  if not _has("volume", "trades"):
    cur.execute("ALTER TABLE trades ADD COLUMN volume REAL")
  if not _has("risk_pct_used", "trades"):
    cur.execute("ALTER TABLE trades ADD COLUMN risk_pct_used REAL")
  con.commit()
  con.close()


if __name__ == "__main__":
  migrate()


