import sqlite3, json, time

DB = None


def init(db_path: str):
    global DB
    DB = db_path
    con = sqlite3.connect(DB)
    con.executescript(
        """
    CREATE TABLE IF NOT EXISTS session_profiles(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      symbol TEXT NOT NULL,
      session TEXT NOT NULL,
      k REAL,
      fixed_pts REAL,
      latency_cap INTEGER,
      queue_json TEXT,
      updated_at INTEGER,
      UNIQUE(symbol, session)
    );
    """
    )
    con.commit()
    con.close()


def load(symbol: str, session: str):
    con = sqlite3.connect(DB)
    r = con.execute(
        "SELECT k,fixed_pts,latency_cap,queue_json,updated_at FROM session_profiles WHERE symbol=? AND session=?",
        (symbol, session),
    ).fetchone()
    con.close()
    if not r:
        return None
    k, fixed_pts, lat_cap, qj, ts = r
    return {"k": k, "fixed_pts": fixed_pts, "latency_cap": lat_cap, "queue": json.loads(qj or "{}"), "updated_at": ts}


def save(symbol: str, session: str, profile: dict):
    con = sqlite3.connect(DB)
    con.execute(
        """INSERT INTO session_profiles(symbol,session,k,fixed_pts,latency_cap,queue_json,updated_at)
                   VALUES (?,?,?,?,?,?,?)
                   ON CONFLICT(symbol,session) DO UPDATE SET
                     k=excluded.k,fixed_pts=excluded.fixed_pts,latency_cap=excluded.latency_cap,
                     queue_json=excluded.queue_json,updated_at=excluded.updated_at
                """,
        (
            symbol,
            session,
            profile["k"],
            profile["fixed_pts"],
            profile["latency_cap"],
            json.dumps(profile.get("queue", {}), ensure_ascii=False),
            int(time.time()),
        ),
    )
    con.commit()
    con.close()


