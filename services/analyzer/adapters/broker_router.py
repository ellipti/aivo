from __future__ import annotations

import json
import math
from typing import List, Tuple

from .interfaces import OrderRequest, OrderResult
from ..trade_executor import load_exec_cfg, place_slippage_aware
from .mt5_adapter import MT5Broker
from ..utils.risk_regime import load_cfg as load_risk_cfg, detect_regime, select_profile


class BrokerRouter:
    def __init__(self, cfg_path: str = "configs/accounts.json"):
        self.cfg = json.load(open(cfg_path, "r", encoding="utf-8"))
        self.brokers: dict[str, tuple[dict, object]] = {}
        for acc in self.cfg.get("accounts", []):
            if acc.get("type") == "mt5":
                b = MT5Broker(
                    login=int(acc["login"]),
                    password=str(acc["password"]),
                    server=str(acc["server"]),
                    host=acc.get("host"),
                    account_id=str(acc["id"]),
                )
                b.connect()
                self.brokers[str(acc["id"])] = (acc, b)

    def _eligible_accounts(self, symbol: str) -> List[tuple[dict, object]]:
        out: List[tuple[dict, object]] = []
        for _acc_id, (acc, b) in self.brokers.items():
            if symbol in acc.get("symbols", []) and getattr(b, "is_healthy", lambda: False)():
                out.append((acc, b))
        return out

    def split_risk(self, symbol: str, lots_total: float) -> List[tuple[dict, object, float]]:
        elig = self._eligible_accounts(symbol)
        if not elig:
            return []
        w_sum = sum(float(a.get("risk_split_weight", 1.0)) for a, _ in elig) or 1.0
        parts: List[tuple[dict, object, float]] = []
        for a, b in elig:
            portion = lots_total * (float(a.get("risk_split_weight", 1.0)) / w_sum)
            portion = math.floor(portion / 0.01) * 0.01
            if portion >= 0.01:
                parts.append((a, b, round(portion, 2)))
        return parts

    def place_across(self, req: OrderRequest, lots_total: float) -> List[tuple[str, OrderResult]]:
        results: List[tuple[str, OrderResult]] = []
        parts = self.split_risk(req.symbol, lots_total)
        for acc, broker, part_lots in parts:
            r = getattr(broker, "place_order")(OrderRequest(
                symbol=req.symbol,
                side=req.side,
                volume=part_lots,
                entry=req.entry,
                sl=req.sl,
                tp=req.tp,
                comment=req.comment,
            ))
            if r.latency_ms > int(acc.get("max_latency_ms", 1000)):
                results.append(
                    (
                        str(acc["id"]),
                        OrderResult(
                            False,
                            None,
                            r.fill_price,
                            r.latency_ms,
                            reason=f"latency {r.latency_ms}ms > max {acc['max_latency_ms']}",
                        ),
                    )
                )
                continue
            if r.ok and r.fill_price is not None:
                point = getattr(broker, "get_point")(req.symbol)
                slip_pts = abs(r.fill_price - req.entry) / max(point, 1e-9)
                if slip_pts > float(acc.get("max_slippage_points", 100)):
                    results.append(
                        (
                            str(acc["id"]),
                            OrderResult(
                                False,
                                r.broker_order_id,
                                r.fill_price,
                                r.latency_ms,
                                reason=f"slippage {slip_pts:.1f}pts > max {acc['max_slippage_points']}",
                            ),
                        )
                    )
                    continue
            results.append((str(acc["id"]), r))
        return results

    def slippage_aware_across(self, req: OrderRequest, lots_total: float):
        cfg = load_exec_cfg(symbol=req.symbol)
        parts = self.split_risk(req.symbol, lots_total)
        outcomes = []
        import time as _t
        # regime-aware lot multiplier per account chunk
        try:
            rr_cfg = load_risk_cfg()
            # We do not have M1 path here; use empty to rely on spread-only for liq and default vol mapping
            last_tick = getattr(next(iter(self.brokers.values()))[1], "get_tick")(req.symbol)
            point = getattr(next(iter(self.brokers.values()))[1], "get_point")(req.symbol)
            regime = detect_regime([], {"bid": last_tick.bid, "ask": last_tick.ask}, point, rr_cfg, req.symbol)
            prof = select_profile(regime, rr_cfg.get("mapping", {}))
            lot_mult = float(prof.get("lot_mult", 1.0)) if rr_cfg.get("apply", {}).get("lot_multiplier", True) else 1.0
        except Exception:
            lot_mult = 1.0
        for acc, broker, vol in parts:
            ok, reason, avg_fill = place_slippage_aware(
                broker=broker,
                oid=f"{req.symbol}-{int(_t.time())}",
                req=OrderRequest(
                    symbol=req.symbol,
                    side=req.side,
                    volume=round(vol * lot_mult, 2),
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
            outcomes.append((acc["id"], ok, reason, avg_fill))
        return outcomes


