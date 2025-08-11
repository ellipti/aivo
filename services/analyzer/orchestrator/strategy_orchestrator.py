from __future__ import annotations

import json, time
from typing import Dict, Any

from ..utils.logger import info
from ..utils.risk_manager import tune_order
from ..utils.portfolio import load_pf_cfg, dynamic_risk_pct, can_open
from ..adapters.broker_router import BrokerRouter
from ..strategies.base import StratDecision


class StrategyBase:
    def name(self) -> str:
        return self.__class__.__name__.lower()

    def should_activate(self, ctx: Dict[str, Any]) -> bool:
        return True

    def next_decision(self, symbol: str, rows) -> StratDecision | None:
        return None


class Scalping(StrategyBase):
    def should_activate(self, ctx: Dict[str, Any]) -> bool:
        return ctx.get("vol") == "HIGH" and ctx.get("session") in ("LONDON", "NY")


class Swing(StrategyBase):
    def should_activate(self, ctx: Dict[str, Any]) -> bool:
        return ctx.get("vol") in ("MID", "LOW")


class NewsTrade(StrategyBase):
    def should_activate(self, ctx: Dict[str, Any]) -> bool:
        return bool(ctx.get("news_within_min", 999) <= 30)


class StrategyOrchestrator:
    def __init__(self, cfg_path: str = "configs/strategies.json"):
        self.cfg = json.load(open(cfg_path, "r", encoding="utf-8"))
        self.router = BrokerRouter()
        self.pf = load_pf_cfg()
        self.strategies: Dict[str, StrategyBase] = {
            "scalping": Scalping(),
            "swing": Swing(),
            "news": NewsTrade(),
        }

    def run_cycle(self, market_ctx: Dict[str, Any]):
        symbol = market_ctx.get("symbol", "XAUUSD")
        rows = market_ctx.get("rows", [])
        if len(rows) < 50:
            return
        for name, strat in self.strategies.items():
            if not self.cfg["enabled"].get(name, True):
                continue
            if not strat.should_activate(market_ctx):
                continue
            # Placeholder: your real decision logic here
            dec: StratDecision | None = None
            if not dec:
                continue
            tick = market_ctx.get("tick", {"bid": 0.0, "ask": 0.0})
            balance = market_ctx.get("balance", 10000.0)
            tuned = tune_order(symbol, balance, rows, tick, dec.entry, dec.side)
            risk_pct_eff = dynamic_risk_pct(symbol, base_pct=1.0, pf_cfg=self.pf)
            mult = float(self.cfg["risk_multiplier"].get(name, 1.0))
            risk_pct_eff *= mult
            ok, reason = can_open(symbol, need_risk_pct=risk_pct_eff, pf_cfg=self.pf)
            if not ok:
                continue
            # Execute via router (example: slippage-aware across accounts)
            # self.router.slippage_aware_across(...)
            info("strategy.exec", strategy=name, symbol=symbol)


