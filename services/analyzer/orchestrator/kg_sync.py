from __future__ import annotations

import time
from ..kg.schema import Graph

KG = Graph()


def on_drift(event, p):
    sym = p.get("symbol")
    nid = KG.add_node("EVENT", kind="DRIFT_ALERT", symbol=sym, ts=int(time.time()))
    sid = KG.add_node("SYMBOL", id=f"SYM:{sym}", symbol=sym)
    KG.add_edge(nid, sid, "INFLUENCES", psi_max=p.get("psi_max"), ks_max=p.get("ks_max"))


def on_perf_cliff(event, p):
    sym = p.get("symbol")
    nid = KG.add_node("EVENT", kind="PERF_CLIFF", symbol=sym, ts=int(time.time()))
    sid = KG.add_node("SYMBOL", id=f"SYM:{sym}", symbol=sym)
    KG.add_edge(nid, sid, "BLOCKED_BY", cum_r=p.get("cum_r"), hit=p.get("hit_pct"))


def on_data_anomaly(event, p):
    sym = p.get("symbol")
    nid = KG.add_node("EVENT", kind="DATA_ANOMALY", symbol=sym, ts=int(time.time()))
    sid = KG.add_node("SYMBOL", id=f"SYM:{sym}", symbol=sym)
    KG.add_edge(nid, sid, "BLOCKED_BY", reason=p.get("reason"))


