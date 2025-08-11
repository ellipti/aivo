import json, time, os
from .timeline_build import summarize_timeline
from ..orchestrator.kg_sync import KG


def _kg_nearby(symbol: str, since: int):
    out = []
    for n in KG.nodes.values():
        if n.type == "EVENT" and n.attrs.get("symbol") == symbol and int(n.attrs.get("ts", 0)) >= since:
            out.append(n.attrs)
    return out


def diagnose(oid: str, symbol: str, cfg: dict):
    tl = summarize_timeline(oid, cfg["timeline_window_sec"])
    evs, kpi = tl["events"], tl["kpi"]
    since = int(time.time()) - int(cfg["rca"]["lookback_sec"])
    kg_events = _kg_nearby(symbol, since)

    factors = []
    if (kpi.get("slip_max", 0) or 0) >= cfg["rca"]["slip_pts_spike"]:
        factors.append({"type": "EXECUTION", "key": "SLIPPAGE_SPIKE", "detail": kpi.get("slip_max", 0)})
    if (kpi.get("latency_max", 0) or 0) >= cfg["rca"]["latency_cap_over_ms"]:
        factors.append({"type": "EXECUTION", "key": "LATENCY_CAP", "detail": kpi.get("latency_max", 0)})
    if any(e.get("kind") == "REGIME" and e.get("liq") == "LOW" for e in evs):
        factors.append({"type": "MARKET", "key": "LOW_LIQ", "detail": "regime_low_liq"})
    if any(e.get("kind") == "ALERT" and e.get("type") == "DRIFT" for e in evs) or any(
        x.get("kind") == "DRIFT_ALERT" for x in kg_events
    ):
        factors.append({"type": "DATA", "key": "FEATURE_DRIFT", "detail": "kg_drift_event"})
    if any(e.get("kind") == "ALERT" and e.get("type") == "DATA" for e in evs):
        factors.append({"type": "DATA", "key": "FEED_ANOM", "detail": "data_integrity"})

    if any(f["key"] == "FEED_ANOM" for f in factors):
        verdict = "DATA_FEED_ANOMALY"
    elif any(f["key"] == "SLIPPAGE_SPIKE" for f in factors) and any(f["key"] == "LOW_LIQ" for f in factors):
        verdict = "LOW_LIQUIDITY_SLIPPAGE"
    elif any(f["key"] == "LATENCY_CAP" for f in factors):
        verdict = "BROKER_LATENCY"
    elif any(f["key"] == "FEATURE_DRIFT" for f in factors):
        verdict = "FEATURE_DRIFT"
    else:
        verdict = "UNCLASSIFIED"

    actions = []
    if verdict in ("LOW_LIQUIDITY_SLIPPAGE", "BROKER_LATENCY"):
        actions.append({"do": "INCREASE_LIMIT_WAIT", "value_ms": 800})
        actions.append({"do": "REDUCE_LOT_MULT", "value": 0.8})
    if verdict == "DATA_FEED_ANOMALY":
        actions.append({"do": "PAUSE", "minutes": 15})
    if verdict == "FEATURE_DRIFT":
        actions.append({"do": "SAFE_MODE", "value": 1})

    return {"verdict": verdict, "factors": factors, "timeline": tl, "actions": actions}


