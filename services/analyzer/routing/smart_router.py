from __future__ import annotations

import json, os, sqlite3, time
from typing import Any, Dict, List, Tuple

from ..adapters.broker_router import BrokerRouter
from ..trade_executor import place_slippage_aware, load_exec_cfg
from ..adapters.interfaces import OrderRequest
from ..utils.logger import info, warn


DB = os.environ.get("AIVO_DB_PATH", "aivo_trades.db")


def _q(sql: str, params=()):
    con = sqlite3.connect(DB)
    try:
        cur = con.execute(sql, params)
        return cur.fetchall()
    finally:
        con.close()


def load_perf_summary() -> Dict[str, Dict[str, float]]:
    # Returns avg latency and slippage per account id from executions table
    rows = _q(
        """
        SELECT account_id, AVG(latency_ms), AVG(slippage_pts)
        FROM executions
        GROUP BY account_id
        """
    )
    return {str(r[0]): {"lat_ms": float(r[1] or 0.0), "slip_pts": float(r[2] or 0.0)} for r in rows}


class SmartRouter:
    def __init__(self, cfg_path: str = "configs/accounts.json"):
        self.router = BrokerRouter(cfg_path)
        self.acc_cfg = json.load(open(cfg_path, "r", encoding="utf-8"))

    def _eligible(self, symbol: str) -> List[Tuple[dict, object]]:
        # reuse BrokerRouter internal elig
        return [x for x in self.router._eligible_accounts(symbol)]  # type: ignore[attr-defined]

    def _score_accounts(self, symbol: str) -> List[Tuple[str, dict, object, float]]:
        perf = load_perf_summary()
        scored: List[Tuple[str, dict, object, float]] = []
        for acc, broker in self._eligible(symbol):
            acc_id = str(acc["id"])
            p = perf.get(acc_id, {"lat_ms": 500.0, "slip_pts": 5.0})
            base = float(acc.get("routing_weight", 1.0))
            penalty = 0.0
            # hard caps
            if p["lat_ms"] > float(acc.get("max_latency_ms", 2000)):
                penalty += 5.0
            score = (p["lat_ms"] / 500.0) + (p["slip_pts"] / 5.0) - 0.1 * base
            scored.append((acc_id, acc, broker, score + penalty))
        scored.sort(key=lambda x: x[3])
        return scored

    def route_order(self, oid: str, req: OrderRequest) -> List[Tuple[str, bool, str, float]]:
        cfg = load_exec_cfg(symbol=req.symbol)
        ranked = self._score_accounts(req.symbol)
        outcomes: List[Tuple[str, bool, str, float]] = []
        for acc_id, acc, broker, _ in ranked:
            ok, reason, avg_fill = place_slippage_aware(
                broker=broker,
                oid=f"{oid}-{acc_id}",
                req=OrderRequest(
                    symbol=req.symbol,
                    side=req.side,
                    volume=max(0.01, round(float(acc.get("min_lot", 0.01)), 2)),
                    entry=req.entry,
                    sl=req.sl,
                    tp=req.tp,
                    comment=req.comment,
                ),
                use_iceberg=bool(cfg["iceberg"]["enabled"]),
                iceberg_chunks=int(cfg["iceberg"]["chunks"]),
                pre_n=int(cfg["pretrade"]["snapshots"]),
                pre_iv_ms=int(cfg["pretrade"]["snapshot_interval_ms"]),
                max_spread_pts=float(cfg["pretrade"]["max_spread_points"]),
                limit_wait_ms=int(cfg["limit"]["wait_fill_ms"]),
                replace_retries=int(cfg["limit"]["replace_retries"]),
                offset_cap_pts=float(cfg["limit"]["offset_points_cap"]),
                vol_k=float(cfg["limit"]["volatility_k"]),
                fallback_policy=cfg.get("fallback", {}),
            )
            outcomes.append((acc_id, ok, reason, avg_fill))
            if ok:
                info("route.ok", account=acc_id, symbol=req.symbol)
            else:
                warn("route.fail", account=acc_id, reason=reason)
        # Failover: if none ok, try again with next best broker by relaxing policy (allow market fallback)
        if not any(o[1] for o in outcomes) and ranked:
            acc_id, acc, broker, _ = ranked[0]
            cfg2 = json.loads(json.dumps(cfg))
            cfg2.setdefault("fallback", {})["allow_market_if_spread_high"] = True
            ok, reason, avg_fill = place_slippage_aware(
                broker=broker,
                oid=f"{oid}-{acc_id}-retry",
                req=req,
                use_iceberg=bool(cfg2["iceberg"]["enabled"]),
                iceberg_chunks=int(cfg2["iceberg"]["chunks"]),
                pre_n=int(cfg2["pretrade"]["snapshots"]),
                pre_iv_ms=int(cfg2["pretrade"]["snapshot_interval_ms"]),
                max_spread_pts=float(cfg2["pretrade"]["max_spread_points"]),
                limit_wait_ms=int(cfg2["limit"]["wait_fill_ms"]),
                replace_retries=int(cfg2["limit"]["replace_retries"]),
                offset_cap_pts=float(cfg2["limit"]["offset_points_cap"]),
                vol_k=float(cfg2["limit"]["volatility_k"]),
                fallback_policy=cfg2.get("fallback", {}),
            )
            outcomes.append((acc_id, ok, reason, avg_fill))
        return outcomes


