import sqlite3, json, statistics as st, time, os

DB = os.environ.get("AIVO_DB_PATH", "aivo_trades.db")
ENS = "configs/ensemble.json"


def summarize(strategy_id, symbol, since_epoch):
    con = sqlite3.connect(DB)
    rows = con.execute(
        """SELECT r_multiple FROM strategy_perf 
                          WHERE strategy_id=? AND symbol=? AND closed_at>=?""",
        (strategy_id, symbol, since_epoch),
    ).fetchall()
    con.close()
    rs = [float(r[0]) for r in rows]
    n = len(rs)
    hit = 100.0 * sum(1 for x in rs if x > 0) / n if n else 0.0
    return n, sum(rs), (hit or 0.0)


if __name__ == "__main__":
    cfg = json.load(open(ENS, "r", encoding="utf-8"))
    lookback = int(time.time()) - 14 * 86400
    for sym in cfg["symbols"]:
        A = cfg["ab_tests"]["groups"]["A"]
        B = cfg["ab_tests"]["groups"]["B"]
        nA, cumA, hitA = 0, 0.0, 0.0
        nB, cumB, hitB = 0, 0.0, 0.0
        for sid in A:
            n, c, h = summarize(sid, sym, lookback)
            nA += n
            cumA += c
            hitA += h
        for sid in B:
            n, c, h = summarize(sid, sym, lookback)
            nB += n
            cumB += c
            hitB += h
        hitA /= max(1, len(A))
        hitB /= max(1, len(B))
        rule = cfg["ab_tests"]["promotion_rule"]
        if nA >= cfg["ab_tests"]["min_trades_per_arm"] and nB >= cfg["ab_tests"]["min_trades_per_arm"]:
            if (cumB - cumA) >= rule["min_cumR_delta"] and (hitB - hitA) >= rule["min_hit_delta_pct"]:
                for s in cfg["strategies"]:
                    if s["id"] in B:
                        s["weight"] = min(2.0, float(s["weight"]) * 1.2)
                    elif s["id"] in A:
                        s["weight"] = max(0.3, float(s["weight"]) * 0.9)
                json.dump(cfg, open(ENS, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
                print(f"Promoted B on {sym}")


