from __future__ import annotations

import json, time, sqlite3, os
from typing import Dict, List
from .integrity import check_ohlcv_gaps, check_candle_wick_anomaly, check_zero_spread
from .drift import collect_features, drift_tests
from .perf_cliff import check_perf_cliff
from .actions import apply_action
from ..utils.logger import info, warn

DB = os.environ.get("AIVO_DB_PATH", "aivo_trades.db")


def load_cfg(path="configs/monitoring.json"):
    return json.load(open(path, "r", encoding="utf-8"))


def latest_rows(symbol: str, timeframe: str, n: int = 600) -> List[Dict]:
    # TODO: Integrate with your data source
    return []


def last_closed_r(symbol: str, n: int = 40) -> List[float]:
    con = sqlite3.connect(DB)
    rows = [
        float(x[0])
        for x in con.execute(
            """SELECT r_multiple FROM closes 
                   WHERE oid IN (SELECT oid FROM trades WHERE symbol=?)
                   ORDER BY closed_at DESC LIMIT ?""",
            (symbol, n),
        )
    ]
    con.close()
    return rows


def push_alert(symbol: str, msg: str, alert_cfg: Dict):
    try:
        if alert_cfg.get("telegram", False):
            # TODO: wire your telegram sender
            pass
        if alert_cfg.get("webhook"):
            # TODO: http post to webhook
            pass
    except Exception as e:
        warn("alert.fail", error=str(e))


def run_checks():
    cfg = load_cfg()
    out = {"alerts": [], "actions": []}
    for sym in cfg["symbols"]:
        rows = latest_rows(sym, cfg["timeframe"], n=600)
        if len(rows) < 50:
            out["alerts"].append({"symbol": sym, "type": "data", "msg": "insufficient bars"})
            continue

        ok_gap, msg_gap = check_ohlcv_gaps(rows[-120:], cfg["data_integrity"]["max_gap_bars"])
        ok_wick, msg_wick = check_candle_wick_anomaly(rows[-1:], cfg["data_integrity"]["max_wick_ratio"])
        zero_spread_bars = sum(1 for r in rows[-50:] if float(r.get("spread", 0) or 0) == 0.0)
        ok_zspr, msg_zspr = check_zero_spread(zero_spread_bars, cfg["data_integrity"]["zero_spread_bars_cap"])

        if not (ok_gap and ok_wick and ok_zspr):
            action = cfg["actions"]["on_data_anomaly"]
            out["actions"].append({"symbol": sym, "action": action, "why": [msg_gap, msg_wick, msg_zspr]})
            push_alert(sym, f"DATA ANOMALY → {action} | {msg_gap}; {msg_wick}; {msg_zspr}", cfg["alerts"])
            apply_action(action)
            continue

        wnd = cfg["feature_drift"]["window_bars"]
        ref = collect_features(rows[-2 * wnd : -wnd])
        cur = collect_features(rows[-wnd:])
        drift = drift_tests(ref, cur, ks_th=cfg["feature_drift"]["ks_threshold"], psi_th=cfg["feature_drift"]["psi_threshold"])
        if any(x["drift"] for x in drift.values()):
            action = cfg["actions"]["on_drift"]
            out["actions"].append({"symbol": sym, "action": action, "drift": drift})
            push_alert(sym, f"FEATURE DRIFT → {action} | {drift}", cfg["alerts"])
            apply_action(action)

        rs = last_closed_r(sym, cfg["perf_cliff"]["lookback_trades"])
        ok_perf, msg_perf = check_perf_cliff(
            rs,
            cfg["perf_cliff"]["min_hit_pct"],
            cfg["perf_cliff"]["min_avg_r"],
            cfg["perf_cliff"]["trigger_drawdown_r"],
        )
        if not ok_perf:
            action = cfg["actions"]["on_perf_cliff"]
            out["actions"].append({"symbol": sym, "action": action, "why": msg_perf})
            push_alert(sym, f"PERF CLIFF → {action} | {msg_perf}", cfg["alerts"])
            apply_action(action)
    return out


