from fastapi import APIRouter
import sqlite3, os, statistics as st, json

DB = os.environ.get("AIVO_DB_PATH", "aivo_trades.db")
router = APIRouter(prefix="/ensemble", tags=["ensemble"])


@router.get("/perf/{symbol}")
def perf(symbol: str):
    con = sqlite3.connect(DB)
    rows = con.execute("""SELECT strategy_id, r_multiple FROM strategy_perf WHERE symbol=?""", (symbol,)).fetchall()
    con.close()
    d: dict[str, list[float]] = {}
    for sid, r in rows:
        d.setdefault(str(sid), []).append(float(r))
    out = []
    for sid, lst in d.items():
        n = len(lst)
        hit = 100.0 * sum(1 for x in lst if x > 0) / n if n else 0.0
        out.append({
            "strategy": sid,
            "n": n,
            "hit": round(hit, 2),
            "avg_r": round(st.mean(lst), 3) if n else 0.0,
            "cum_r": round(sum(lst), 3)
        })
    out.sort(key=lambda x: (x["cum_r"], x["avg_r"]), reverse=True)
    return out


