from __future__ import annotations

import time
import json
from typing import List, Tuple
import os

from .adapters.interfaces import OrderRequest, OrderResult, Tick, BaseBroker
from .utils.execution_log import log_exec
from .utils.logger import info, warn
from datetime import datetime, timezone
from .utils.risk_regime import load_cfg as load_risk_cfg, detect_regime, select_profile, adjust_tp_sl_rr
from .backtest.data_loader import load_m1_csv


def _deep_merge(a: dict, b: dict) -> dict:
    out = dict(a)
    for k, v in (b or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _session_now_utc(sessions_utc: dict):
    h = datetime.now(timezone.utc).hour
    for name, rng in sessions_utc.items():
        lo, hi = rng
        if lo <= hi and lo <= h <= hi:
            return name
        if lo > hi and (h >= lo or h <= hi):
            return name
    return "OTHER"


def load_exec_cfg(symbol: str | None = None, path: str = "configs/execution.json", sessions_file: str = "configs/online_calib.json"):
    base = json.load(open(path, "r", encoding="utf-8"))
    if symbol:
        alt = f"configs/execution.{str(symbol).upper()}.json"
        if os.path.exists(alt):
            base = _deep_merge(base, json.load(open(alt, "r", encoding="utf-8")))
        if os.path.exists(sessions_file):
            sess_cfg = json.load(open(sessions_file, "r", encoding="utf-8")).get("sessions_utc", {})
            cur_sess = _session_now_utc(sess_cfg)
            alt2 = f"configs/execution.{str(symbol).upper()}.{cur_sess}.json"
            if os.path.exists(alt2):
                base = _deep_merge(base, json.load(open(alt2, "r", encoding="utf-8")))
    return base


def _snapshots(broker: BaseBroker, symbol: str, n: int, iv_ms: int) -> List[Tick]:
    out: List[Tick] = []
    for _ in range(n):
        out.append(broker.get_tick(symbol))
        time.sleep(iv_ms / 1000.0)
    return out


def _spread_pts(t: Tick, point: float) -> float:
    return abs(t.ask - t.bid) / max(point, 1e-9)


def _volatility_pts(snaps: List[Tick], point: float) -> float:
    if len(snaps) < 2:
        return 0.0
    rng = max(abs(snaps[-1].ask - snaps[0].ask), abs(snaps[-1].bid - snaps[0].bid))
    return rng / max(point, 1e-9)


def _calc_offset_pts(vol_pts: float, cap: float, k: float) -> float:
    return min(cap, k * vol_pts)


def _split_iceberg(total: float, chunks: int) -> List[float]:
    base = max(0.01, round(total / max(1, chunks), 2))
    parts = [base] * (max(1, chunks) - 1)
    last = round(total - sum(parts), 2)
    return [p for p in parts + [last] if p >= 0.01]


def place_slippage_aware(
    broker: BaseBroker,
    oid: str,
    req: OrderRequest,
    *,
    use_iceberg: bool,
    iceberg_chunks: int,
    pre_n: int,
    pre_iv_ms: int,
    max_spread_pts: float,
    limit_wait_ms: int,
    replace_retries: int,
    offset_cap_pts: float,
    vol_k: float,
    fallback_policy: dict | None = None,
) -> Tuple[bool, str, float]:
    point = broker.get_point(req.symbol)
    # Regime-aware adjustments (pre-trade)
    try:
        rr_cfg = load_risk_cfg()
        # Load last N M1 rows for ATR calc if path available in backtest config; optional safety
        m1_path = None
        # attempt to use execution config hint path if exists
        # Fallback: skip if no data
        m1_rows = []
        if m1_path and os.path.exists(m1_path):
            m1_rows = load_m1_csv(m1_path)[-100:]
        last_tick = {"bid": broker.get_tick(req.symbol).bid, "ask": broker.get_tick(req.symbol).ask}
        regime = detect_regime(m1_rows, last_tick, point, rr_cfg, req.symbol)
        prof = select_profile(regime, rr_cfg.get("mapping", {}))
        if rr_cfg.get("apply", {}).get("tp_sl", True):
            # only adjust if req has entry; keep SL/TP if already provided
            base_entry = req.entry
            if base_entry:
                new_tp, new_sl, _ = adjust_tp_sl_rr(base_entry, req.side, point, prof)
                req = OrderRequest(
                    symbol=req.symbol,
                    side=req.side,
                    volume=req.volume * float(prof.get("lot_mult", 1.0)) if rr_cfg.get("apply", {}).get("lot_multiplier", True) else req.volume,
                    entry=req.entry,
                    sl=(req.sl or new_sl),
                    tp=(req.tp or new_tp),
                    comment=req.comment,
                )
    except Exception:
        pass
    snaps = _snapshots(broker, req.symbol, n=pre_n, iv_ms=pre_iv_ms)
    spread_bad = any(_spread_pts(s, point) > max_spread_pts for s in snaps)
    if spread_bad:
        warn("pretrade.spread.high", symbol=req.symbol)
        if fallback_policy and fallback_policy.get("allow_market_if_spread_high"):
            mres = broker.place_market(req)
            status = "OK" if mres.ok else "REJECT"
            slip_pts = (
                abs((mres.fill_price or req.entry) - req.entry) / max(point, 1e-9)
                if mres.fill_price
                else 0.0
            )
            log_exec(
                oid,
                getattr(broker, "account_id", "acc"),
                req.symbol,
                req.side,
                req.entry,
                mres.fill_price or None,
                req.sl,
                req.tp,
                volume=req.volume,
                latency_ms=mres.latency_ms,
                slippage_pts=slip_pts,
                status=status,
                reason=("market_fallback" if mres.ok else f"market_fail:{mres.reason}"),
            )
            return (bool(mres.ok), ("market_ok" if mres.ok else "market_fail"), float(mres.fill_price or 0.0))
        return (False, "spread_too_high", 0.0)

    vol_pts = _volatility_pts(snaps, point)
    offset_pts = _calc_offset_pts(vol_pts, cap=offset_cap_pts, k=vol_k)

    volumes = _split_iceberg(req.volume, iceberg_chunks) if use_iceberg else [req.volume]

    fills: List[float] = []
    for i, vol in enumerate(volumes, start=1):
        limit_px = (req.entry - offset_pts * point) if req.side == "BUY" else (req.entry + offset_pts * point)

        sub_req = OrderRequest(
            symbol=req.symbol,
            side=req.side,
            volume=vol,
            entry=req.entry,
            sl=req.sl,
            tp=req.tp,
            comment=req.comment,
        )
        res = broker.place_limit(sub_req, limit_px, tif_ms=limit_wait_ms)
        status = "PLACED" if res.ok else "REJECT"
        log_exec(
            oid,
            getattr(broker, "account_id", "acc"),
            req.symbol,
            req.side,
            req.entry,
            res.fill_price,
            req.sl,
            req.tp,
            volume=vol,
            latency_ms=res.latency_ms,
            slippage_pts=0.0,
            status=status,
            reason=res.reason,
        )

        if not res.ok:
            return (False, f"limit_place_failed_{i}", 0.0)

        broker_id = res.broker_order_id or ""
        filled = False
        retry = 0
        t0 = time.time()
        while (time.time() - t0) * 1000 < limit_wait_ms:
            time.sleep(0.15)
            if broker.position_filled(broker_id):
                filled = True
                break

        while not filled and retry < replace_retries:
            broker.cancel(broker_id)
            snaps2 = _snapshots(broker, req.symbol, n=2, iv_ms=pre_iv_ms)
            vol2 = _volatility_pts(snaps2, point)
            off2 = _calc_offset_pts(vol2, cap=offset_cap_pts, k=vol_k)
            limit_px = (req.entry - off2 * point) if req.side == "BUY" else (req.entry + off2 * point)

            res2 = broker.place_limit(sub_req, limit_px, tif_ms=limit_wait_ms)
            log_exec(
                oid,
                getattr(broker, "account_id", "acc"),
                req.symbol,
                req.side,
                req.entry,
                res2.fill_price,
                req.sl,
                req.tp,
                volume=vol,
                latency_ms=res2.latency_ms,
                slippage_pts=0.0,
                status=("REPLACED_PLACED" if res2.ok else "REPLACED_REJECT"),
                reason=res2.reason,
            )
            if not res2.ok:
                return (False, f"replace_failed_{i}", 0.0)

            broker_id = res2.broker_order_id or ""
            t0 = time.time()
            while (time.time() - t0) * 1000 < limit_wait_ms:
                time.sleep(0.15)
                if broker.position_filled(broker_id):
                    filled = True
                    break
            retry += 1

        if not filled:
            broker.cancel(broker_id)
            warn("chunk.unfilled.cancelled", chunk=i)
            return (False, "partial_or_timeout", 0.0)

        last = broker.get_tick(req.symbol)
        fills.append(last.ask if req.side == "BUY" else last.bid)
        time.sleep(max(0.0, pre_iv_ms / 1000.0))

    avg_fill = sum(fills) / len(fills) if fills else 0.0
    slip_pts = abs(avg_fill - req.entry) / max(point, 1e-9)
    log_exec(
        oid,
        getattr(broker, "account_id", "acc"),
        req.symbol,
        req.side,
        req.entry,
        avg_fill,
        req.sl,
        req.tp,
        volume=req.volume,
        latency_ms=0,
        slippage_pts=slip_pts,
        status="FILLED",
        reason="slippage_summary",
    )
    info("slippage.summary", pts=round(slip_pts, 2), avg_fill=round(avg_fill, 3))
    return (True, "ok", avg_fill)


