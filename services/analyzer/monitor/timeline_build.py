import json, time
from pathlib import Path

EVP = Path("incidents/_events.jsonl")


def load_events(oid: str, window_sec: int):
    if not EVP.exists():
        return []
    now = int(time.time())
    out = []
    with open(EVP, "r", encoding="utf-8") as f:
        for ln in f:
            try:
                e = json.loads(ln)
                if e.get("oid") == oid and now - int(e.get("t", 0)) <= window_sec:
                    out.append(e)
            except Exception:
                pass
    return sorted(out, key=lambda x: x["t"])


def summarize_timeline(oid: str, window_sec: int):
    evs = load_events(oid, window_sec)
    if not evs:
        return {"events": [], "kpi": {}}
    kpi = {"slip_max": 0.0, "latency_max": 0, "replaces": 0}
    for e in evs:
        if e.get("kind") == "EXEC":
            kpi["latency_max"] = max(kpi["latency_max"], int(e.get("latency_ms") or 0))
            kpi["slip_max"] = max(kpi["slip_max"], float(e.get("slip_pts") or 0))
            if e.get("step") == "REPLACE":
                kpi["replaces"] += 1
    return {"events": evs, "kpi": kpi}


