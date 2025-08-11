import sqlite3, os, csv


def load_execs(db_path: str, symbol: str):
    con = sqlite3.connect(db_path)
    cur = con.execute(
        """
      SELECT account_id, symbol, side, req_entry, fill_price, latency_ms, slippage_pts, ts, status
      FROM executions WHERE symbol=? AND status IN ('OK','FILLED') AND fill_price IS NOT NULL
    """,
        (symbol,),
    )
    rows = [
        dict(account=r[0], symbol=r[1], side=r[2], req=r[3], fill=r[4], lat=r[5] or 0, slip=r[6] or 0, ts=r[7], status=r[8])
        for r in cur.fetchall()
    ]
    con.close()
    return rows


def load_m1(csv_path: str):
    out = []
    if not (csv_path and os.path.exists(csv_path)):
        return out
    with open(csv_path, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out.append(
                dict(t=int(r["time"]), o=float(r["open"]), h=float(r["high"]), l=float(r["low"]), c=float(r["close"]), spr=float(r.get("spread", 0) or 0))
            )
    return out


def spread_pts_proxy(m1_rows, point: float):
    d = {}
    for r in m1_rows:
        spr = r["spr"] if r["spr"] > 0 else 0.05 * (r["h"] - r["l"])
        d[r["t"]] = max(1.0, spr / point)
    return d


def pctile(values, p):
    if not values:
        return 0
    vs = sorted(values)
    k = max(0, min(len(vs) - 1, int(round((p / 100.0) * (len(vs) - 1)))))
    return vs[k]


