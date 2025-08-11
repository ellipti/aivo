from fastapi import APIRouter
import sqlite3, os, json, time
from .monitor.rca import diagnose
from .monitor.postmortem import md_report

DB = os.environ.get("AIVO_DB_PATH", "aivo_trades.db")
CFG = json.load(open("configs/incidents.json", "r", encoding="utf-8"))
router = APIRouter(prefix="/incidents", tags=["incidents"])


def _q(sql, params=()):
    con = sqlite3.connect(DB)
    cur = con.execute(sql, params)
    rows = cur.fetchall()
    con.close()
    return rows


@router.get("/list")
def list_incidents(limit: int = 50):
    rows = _q("SELECT oid,symbol,strategy_id,verdict,created_at FROM incidents ORDER BY created_at DESC LIMIT ?", (limit,))
    return [{"oid": r[0], "symbol": r[1], "strategy": r[2], "verdict": r[3], "created_at": r[4]} for r in rows]


@router.post("/analyze/{oid}")
def analyze(oid: str, symbol: str, strategy: str):
    res = diagnose(oid, symbol, CFG)
    con = sqlite3.connect(DB)
    con.execute(
        """INSERT OR REPLACE INTO incidents(oid,symbol,strategy_id,opened_at,closed_at,pnl_r,pnl_points,verdict,factors_json,actions_json,created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (oid, symbol, strategy, None, None, None, None, res["verdict"], json.dumps(res["factors"]), json.dumps(res["actions"]), int(time.time())),
    )
    con.commit()
    con.close()
    path = md_report(oid, symbol, strategy, res, CFG["export"]["md_dir"])
    return {"verdict": res["verdict"], "factors": res["factors"], "actions": res["actions"], "report_md": path}


