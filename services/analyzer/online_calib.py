from __future__ import annotations

import json, time
from datetime import datetime, timezone

from .calib.data import load_execs, load_m1, spread_pts_proxy
from .calib.slip_latency import fit_slippage_k, fit_latency
from .calib.queue_fit import fit_queue
from .calib.profile_store import init as ps_init, load as ps_load, save as ps_save


def in_session(ts_utc: int, sess):
    h = datetime.fromtimestamp(ts_utc, tz=timezone.utc).hour
    lo, hi = sess
    if lo <= hi:
        return lo <= h <= hi
    return (h >= lo) or (h <= hi)


def ema(prev, new, alpha):
    return round(alpha * new + (1 - alpha) * (prev if prev is not None else new), 3)


def guard_jump(prev, new, safety):
    if not prev:
        return True, ""
    if abs(new["k"] - prev["k"]) > safety["max_k_jump_abs"]:
        return False, "k_jump"
    if abs(new["fixed_pts"] - prev["fixed_pts"]) > safety["max_fixed_pts_jump_abs"]:
        return False, "fixed_pts_jump"
    old = max(1, prev["latency_cap"])
    inc = 100.0 * (new["latency_cap"] - old) / old
    if abs(inc) > safety["max_latency_cap_jump_pct"]:
        return False, "latency_jump"
    return True, ""


def run_once(conf_path="configs/online_calib.json"):
    cfg = json.load(open(conf_path, "r", encoding="utf-8"))
    ps_init(cfg["out"]["profiles_db"])

    sessions = cfg["sessions_utc"]
    report = {"updated": [], "skipped": []}

    for sym in cfg["symbols"]:
        execs = load_execs(cfg["db_path"], sym)
        if not execs:
            report["skipped"].append({"symbol": sym, "reason": "no_execs"})
            continue
        cutoff = int(time.time()) - cfg["rolling_days"] * 86400
        execs = [r for r in execs if r["ts"] >= cutoff]

        m1 = load_m1(cfg.get("m1_csv", {}).get(sym)) if cfg.get("m1_csv") else []
        spmap = spread_pts_proxy(m1, cfg["point"][sym]) if m1 else {}

        for sess_name, hours in sessions.items():
            sess_ex = [r for r in execs if in_session(r["ts"], hours)]
            if len(sess_ex) < cfg["min_execs_per_session"]:
                report["skipped"].append({"symbol": sym, "session": sess_name, "n": len(sess_ex), "reason": "min_execs"})
                continue

            slip = fit_slippage_k(sess_ex, spmap, cfg["point"][sym])
            lat = fit_latency(sess_ex)
            qfit = fit_queue(sess_ex)

            prev = ps_load(sym, sess_name)
            blended = {
                "k": ema(prev["k"] if prev else None, slip["k"], cfg["ema_alpha"]),
                "fixed_pts": round(ema(prev["fixed_pts"] if prev else None, slip["fixed_pts"], cfg["ema_alpha"]), 2),
                "latency_cap": int(ema(prev["latency_cap"] if prev else None, lat["cap"], cfg["ema_alpha"])),
                "queue": qfit,
            }

            ok, why = guard_jump(prev, blended, cfg["safety"])
            if not ok:
                report["skipped"].append({"symbol": sym, "session": sess_name, "reason": why, "new": blended, "prev": prev})
                continue

            ps_save(sym, sess_name, blended)

            if cfg.get("update_files", True):
                outp = f'{cfg["out"]["exec_overrides_dir"]}/execution.{sym}.{sess_name}.json'
                spec = {
                    "limit": {"offset_points_cap": max(5, int(round(0.9 * blended["fixed_pts"] + 10 * blended["k"])))},
                    "fallback": {"max_market_slippage_points": max(6, int(round(2 * blended["fixed_pts"] + 8 * blended["k"])))},
                    "pretrade": {"max_spread_points": max(6, int(round((blended["fixed_pts"] / 2) + 12 * blended["k"])))}
                }
                json.dump(spec, open(outp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

            report["updated"].append({"symbol": sym, "session": sess_name, "profile": blended})

    json.dump(report, open(cfg["out"]["report_path"], "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return report


if __name__ == "__main__":
    print(json.dumps(run_once(), ensure_ascii=False, indent=2))


