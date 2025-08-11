import json, os
from .calib.data import load_execs, load_m1, spread_pts_proxy
from .calib.slip_latency import fit_slippage_k, fit_latency
from .calib.queue_fit import fit_queue


def deep_merge(a, b):
    out = dict(a)
    for k, v in (b or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def update_exec_override(sym, base_cfg_path, overrides_dir, slip_k, fixed_pts, lat_cap):
    base = json.load(open(base_cfg_path, "r", encoding="utf-8"))
    spec = {
        "limit": {"offset_points_cap": max(5, int(round(0.9 * fixed_pts + 10 * slip_k)))},
        "fallback": {"max_market_slippage_points": max(6, int(round(2 * fixed_pts + 8 * slip_k)))},
        "pretrade": {"max_spread_points": max(6, int(round((fixed_pts / 2) + 12 * slip_k)))},
    }
    out = deep_merge(base, spec)
    outp = os.path.join(overrides_dir, f"execution.{sym}.json")
    json.dump(out, open(outp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return outp


def update_ticksim(sym, ticksim_path, qfit, point):
    d = json.load(open(ticksim_path, "r", encoding="utf-8")) if os.path.exists(ticksim_path) else {}
    d["symbol"] = sym
    d["point"] = point
    d["engine"] = deep_merge(
        d.get("engine", {}),
        {
            "queue_init_depth": qfit["queue_init_depth"],
            "arrival_rate_lambda": qfit["arrival_rate_lambda"],
            "cancel_rate_mu": qfit["cancel_rate_mu"],
            "aggress_ratio": qfit["aggress_ratio"],
        },
    )
    json.dump(d, open(ticksim_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return ticksim_path


if __name__ == "__main__":
    cfg = json.load(open("configs/calibration.json", "r", encoding="utf-8"))
    report = {}
    for sym in cfg["symbols"]:
        execs = load_execs(cfg["db_path"], sym)
        if len(execs) < cfg["min_execs"]:
            report[sym] = {"status": "insufficient_execs", "n": len(execs)}
            continue
        m1 = load_m1(cfg["m1_csv"].get(sym))
        spmap = spread_pts_proxy(m1, cfg["point"][sym])

        slip = fit_slippage_k(execs, spmap, cfg["point"][sym])
        lat = fit_latency(execs)
        qfit = fit_queue(execs)

        paths = {}
        if cfg.get("update_files", True):
            paths["exec_override"] = update_exec_override(
                sym,
                "configs/execution.json",
                cfg["out"]["exec_overrides_dir"],
                slip["k"],
                slip["fixed_pts"],
                lat["cap"],
            )
            paths["ticksim"] = update_ticksim(sym, cfg["out"]["ticksim_path"], qfit, cfg["point"][sym])

        report[sym] = {
            "status": "ok",
            "n_execs": len(execs),
            "slippage_k": slip["k"],
            "fixed_pts": slip["fixed_pts"],
            "latency_avg": lat["avg"],
            "latency_p95": lat["p95"],
            "latency_cap": lat["cap"],
            "queue": qfit,
            "updated_paths": paths,
        }
    json.dump(report, open(cfg["out"]["report_path"], "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))


