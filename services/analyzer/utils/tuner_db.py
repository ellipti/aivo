import sqlite3, os, time, json

DB = os.environ.get("AIVO_TUNER_DB", "aivo_tuner.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS tuner_runs(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  started_at INTEGER NOT NULL,
  finished_at INTEGER,
  window_start INTEGER,
  window_end INTEGER,
  params TEXT,
  closed INT,
  hit_rate REAL,
  avg_r REAL,
  cum_r REAL,
  accepted INT DEFAULT 0,
  note TEXT
);
CREATE INDEX IF NOT EXISTS idx_tuner_finished ON tuner_runs(finished_at);
"""


def _conn():
  con = sqlite3.connect(DB)
  con.execute("PRAGMA journal_mode=WAL;")
  return con


def init():
  with _conn() as c:
    c.executescript(SCHEMA)


def add_run(window_start, window_end, params):
  with _conn() as c:
    cur = c.execute(
      "INSERT INTO tuner_runs(started_at,window_start,window_end,params) VALUES (?,?,?,?)",
      (int(time.time()), window_start, window_end, json.dumps(params)),
    )
    return cur.lastrowid


def finish_run(run_id, metrics, accepted=False, note=""):
  with _conn() as c:
    c.execute(
      """UPDATE tuner_runs SET finished_at=?, closed=?, hit_rate=?, avg_r=?, cum_r=?, accepted=?, note=?
                     WHERE id=?""",
      (
        int(time.time()),
        metrics.get("closed_trades", 0),
        metrics.get("hit_rate_pct", 0.0),
        metrics.get("avg_r", 0.0),
        metrics.get("cum_r", 0.0),
        1 if accepted else 0,
        note,
        run_id,
      ),
    )


def last_accepted():
  with _conn() as c:
    r = c.execute("SELECT params FROM tuner_runs WHERE accepted=1 ORDER BY finished_at DESC LIMIT 1").fetchone()
    return json.loads(r[0]) if r else None


