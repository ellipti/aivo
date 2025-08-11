from fastapi import APIRouter
from .orchestrator.strategy_orchestrator import StrategyOrchestrator

router = APIRouter(prefix="/strategy", tags=["strategy"])
ORCH = StrategyOrchestrator()


@router.post("/run")
def run_strategy_cycle(market_ctx: dict):
    ORCH.run_cycle(market_ctx)
    return {"ok": True}


