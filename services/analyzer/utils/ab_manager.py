from __future__ import annotations

import json, os, time, random, sqlite3
from typing import List

DB = os.environ.get("AIVO_DB_PATH", "aivo_trades.db")


def load_cfg(path: str = "configs/ensemble.json"):
    return json.load(open(path, "r", encoding="utf-8"))


def assign_group(oid: str, symbol: str, chosen_strats: List[str]):
    con = sqlite3.connect(DB)
    con.execute(
        "INSERT OR REPLACE INTO ab_assign(oid,symbol,group_id,strategies,assigned_at) VALUES (?,?,?,?,?)",
        (oid, symbol, "AB", json.dumps(chosen_strats), int(time.time())),
    )
    con.commit()
    con.close()


def pick_ab_strategies(symbol: str, ens_cfg: dict) -> List[str] | None:
    ab = ens_cfg["ab_tests"]
    if not ab.get("enabled", False):
        return None
    if random.random() > (float(ab.get("traffic_pct", 0)) / 100.0):
        return None
    grp = random.choice(["A", "B"])
    return ens_cfg["ab_tests"]["groups"][grp]


