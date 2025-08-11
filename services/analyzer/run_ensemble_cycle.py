from __future__ import annotations

from types import SimpleNamespace
from .utils.ensemble import load_ens, blend_scores, update_perf_ema
from .utils.ab_manager import pick_ab_strategies, assign_group
from .utils.risk_manager import tune_order
from .utils.portfolio import load_pf_cfg, dynamic_risk_pct, can_open
from .utils.db import record_open
from .utils.logger import info
from .adapters.broker_router import BrokerRouter
from .strategies.base import StrategyAdapter, StratDecision

# Placeholders for your data access
def load_latest_ohlcv_rows(symbol: str, timeframe: str):
    return []

def get_latest_tick(symbol: str):
    return {"bid": 0.0, "ask": 0.0}

def get_account_balance():
    return 10000.0


PF = load_pf_cfg()
ROUTER = BrokerRouter()

# You should implement/plug your strategies here
def build_strategies():
    from .strategies.base import StrategyAdapter  # type: ignore
    return {}


def next_decision(symbol: str, rows):
    ens = load_ens()
    ab_list = pick_ab_strategies(symbol, ens) or [s["id"] for s in ens["strategies"]]
    strategies = build_strategies()
    decs: list[StratDecision] = []
    for s in ens["strategies"]:
        if s["id"] not in ab_list:
            continue
        strat = strategies.get(s["id"])  # type: ignore
        if not strat:
            continue
        d = strat.next(symbol, rows)
        if not d or not d.ok or d.score < s["min_conf"]:
            continue
        d.score = d.score * float(s.get("weight", 1.0))
        decs.append(d)
    chosen = blend_scores(decs, symbol, ens)
    return chosen


def run_cycle(symbol: str, timeframe: str):
    rows = load_latest_ohlcv_rows(symbol, timeframe)
    if len(rows) < 50:
        return
    dec = next_decision(symbol, rows)
    if not dec:
        return

    tick = get_latest_tick(symbol)
    balance = get_account_balance()
    tuned = tune_order(symbol, balance, rows, tick, dec.entry, dec.side)

    risk_pct_eff = dynamic_risk_pct(symbol, base_pct=1.0, pf_cfg=PF) * tuned["lot_mult"]
    ok, reason = can_open(symbol, need_risk_pct=risk_pct_eff, pf_cfg=PF)
    if not ok:
        return

    req = SimpleNamespace(decision=dec.side, entry=tuned["entry"], sl=tuned["sl"], tp=tuned["tp"])
    # Here you would call your executor. Example placeholder:
    # ROUTER.slippage_aware_across(...)

    oid = f"{symbol}-{dec.strategy_id}-{int(__import__('time').time())}"
    assign_group(oid, symbol, [dec.strategy_id])
    record_open(oid, symbol, dec.side, tuned["entry"], tuned["sl"], tuned["tp"], note=f"{dec.strategy_id} | {dec.reason}")
    info("ensemble.exec", symbol=symbol, strategy=dec.strategy_id, side=dec.side, score=dec.score)


