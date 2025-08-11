from __future__ import annotations

import json, multiprocessing as mp, time, os
from typing import List, Tuple
from datetime import datetime, timezone

from .backtest_engine import load_csv, simulate_walk_forward, BtConfig, Candle
from .strategies.aivo_guarded import AIVOGuardedStrategy
from .utils.tuner_db import init as db_init, add_run, finish_run, last_accepted
from .utils.logger import info, warn


def _slice_rolling(candles: List[Candle], bars: int) -> List[Candle]:
    return candles[-bars:] if len(candles) > bars else candles[:]


def _metrics_of(csv_path, guardrails, rr, minstop, window_bars) -> Tuple[dict, int, int]:
    c = load_csv(csv_path)
    w = _slice_rolling(c, window_bars)
    if len(w) < 100:
        return {"closed_trades": 0, "hit_rate_pct": 0, "avg_r": 0, "cum_r": 0}, 0, 0
    train = int(window_bars * 0.7)
    test = max(200, int(window_bars * 0.3))
    strat = AIVOGuardedStrategy(guardrails_path=guardrails, rr=rr, stop_pts_min=minstop)
    cfg = BtConfig(walk_train_bars=train, walk_test_bars=test, rr=rr, min_stop_pts=minstop)
    res = simulate_walk_forward(w, cfg, strat)
    return res, w[0].t, w[-1].t


def _gen_candidates(base, jitter):
    for j_rr in jitter["rr"]:
        for j_ms in jitter["min_stop_pts"]:
            yield {"rr": round(max(0.8, base["rr"] + j_rr), 2), "min_stop_pts": max(2, base["min_stop_pts"] + j_ms)}


def _cooldown_ok(stamp_file="tuner.cooldown", minutes=60):
    if not os.path.exists(stamp_file):
        return True
    return (time.time() - os.path.getmtime(stamp_file)) >= minutes * 60


def _touch(stamp_file="tuner.cooldown"):
    open(stamp_file, "w", encoding="utf-8").write(datetime.utcnow().isoformat())


def run_once(conf_path="configs/tuner.json"):
    cfg = json.load(open(conf_path, "r", encoding="utf-8"))
    db_init()
    base = cfg["base_params"]
    accepted_prev = last_accepted() or base
    if not _cooldown_ok(minutes=cfg["cooldown_minutes"]):
        warn("tuner.cooldown.active")
        return "cooldown"

    cands = list(_gen_candidates(accepted_prev, cfg["candidate_jitter"]))[: cfg["batch_size"]]
    rows = []
    with mp.Pool(processes=min(len(cands), mp.cpu_count())) as pool:
        tasks = []
        for p in cands:
            run_id = add_run(0, 0, p)
            tasks.append((run_id, p))

        def _work(run_id, p):
            res, wstart, wend = _metrics_of(
                cfg["csv_path"], cfg["guardrails_path"], p["rr"], p["min_stop_pts"], cfg["rolling_window_bars"]
            )
            finish_run(run_id, res, accepted=False, note=f"{wstart}-{wend}")
            return {"id": run_id, "params": p, "metrics": res}

        rows = pool.starmap(_work, tasks)

    rows.sort(key=lambda r: (r["metrics"]["cum_r"], r["metrics"]["hit_rate_pct"]), reverse=True)
    best = rows[0]
    ref_metrics, _, _ = _metrics_of(
        cfg["csv_path"], cfg["guardrails_path"], accepted_prev["rr"], accepted_prev["min_stop_pts"], cfg["rolling_window_bars"]
    )

    rules = cfg["accept_rules"]
    ok = (
        best["metrics"]["closed_trades"] >= rules["min_closed"]
        and best["metrics"]["cum_r"] >= ref_metrics["cum_r"] + rules["improve_cum_r"]
        and best["metrics"]["hit_rate_pct"] + 1e-9 >= ref_metrics["hit_rate_pct"] - rules["no_hit_rate_drop_pct"]
    )
    if ok:
        gr_path = cfg["guardrails_path"]
        gr = json.load(open(gr_path, "r", encoding="utf-8"))
        gr["regimes"]["min_score_by_regime"]["NORMAL"] = max(55, min(75, 60 if best["params"]["rr"] >= 2 else 58))
        gr["risk"]["min_stop_pts"] = best["params"]["min_stop_pts"]
        json.dump(gr, open(gr_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        _touch()
        from .utils.tuner_db import _conn

        with _conn() as c:
            c.execute("UPDATE tuner_runs SET accepted=1 WHERE id=?", (best["id"],))
        info(
            "tuner.accepted",
            rr=best["params"]["rr"],
            min_stop=best["params"]["min_stop_pts"],
            cum_r=best["metrics"]["cum_r"],
            hit=best["metrics"]["hit_rate_pct"],
        )
        return {"accepted": best}
    else:
        warn("tuner.rejected", reason="rules not met", best=best["metrics"], ref=ref_metrics)
        return {"rejected": best, "ref": ref_metrics}


if __name__ == "__main__":
    print(run_once())


