from __future__ import annotations

import json, csv, random
from .loader import load_ticks
from .executor import simulate_limit_fill
from .tpsl import follow_tpsl


def run_once(cfg: dict, seed: int = 42):
    random.seed(seed)
    ticks = load_ticks(cfg["data"]["tick_path"])
    if not ticks:
        return {"error": "no ticks"}

    eng = cfg["engine"]
    od = cfg["order"]
    p = cfg["point"]
    entry = od["entry"]
    res = simulate_limit_fill(
        ticks=ticks,
        side=od["side"],
        entry=entry,
        sl=od["sl"],
        tp=od["tp"],
        lots=od["lots"],
        point=p,
        offset_pts=od["place_offset_pts"],
        q_init=eng["queue_init_depth"],
        lam=eng["arrival_rate_lambda"],
        mu=eng["cancel_rate_mu"],
        aggress=eng["aggress_ratio"],
        impact_k=eng["mkt_impact_k"],
        max_wait_ms=eng["max_wait_ms"],
    )
    evs = []

    def emit(e):
        evs.append(e)

    if not res.ok:
        emit({"type": "open_fail", "reason": res.reason, "wait_ms": res.waited_ms})
        return {"ok": False, "reason": res.reason}

    emit({"type": "open", "fill": res.fill_price, "wait_ms": res.waited_ms, "slip_pts": res.slip_pts})
    ex = follow_tpsl(side=od["side"], fill_px=res.fill_price, sl=od["sl"], tp=od["tp"], ticks=ticks)
    emit({"type": "close", "exit": ex.exit, "exit_px": ex.exit_px, "dur_ms": ex.dur_ms})

    if od["side"] == "BUY":
        pnl_pts = ex.exit_px - res.fill_price
        risk_pts = abs(entry - od["sl"])
    else:
        pnl_pts = res.fill_price - ex.exit_px
        risk_pts = abs(od["sl"] - entry)
    r = pnl_pts / max(1e-9, risk_pts)

    with open(cfg["out"]["trades_csv"], "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["side", "fill", "exit", "pnl_pts", "r"])
        w.writerow([od["side"], round(res.fill_price, 3), ex.exit, round(pnl_pts, 2), round(r, 3)])
    with open(cfg["out"]["events_jsonl"], "w", encoding="utf-8") as f:
        f.write("\n".join([json.dumps(e, ensure_ascii=False) for e in evs]))
    stats = {"ok": True, "exit": ex.exit, "pnl_pts": round(pnl_pts, 2), "r": round(r, 3), "slip_pts": round(res.slip_pts, 2)}
    with open(cfg["out"]["stats_json"], "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    return stats


def run_mc(cfg: dict):
    runs = int(cfg.get("mc", {}).get("runs", 1))
    outs = []
    for i in range(runs):
        s = run_once(cfg, seed=41 + i)
        if s.get("ok"):
            outs.append(s)
    if outs:
        import statistics as st

        return {
            "runs": len(outs),
            "hit_pct": round(100.0 * sum(1 for x in outs if x["r"] > 0) / len(outs), 2),
            "avg_r": round(st.mean(x["r"] for x in outs), 3),
            "avg_slip_pts": round(st.mean(x["slip_pts"] for x in outs), 2),
        }
    return {"runs": 0}


