from fastapi import APIRouter
from .optimizer.engine import OptimizerEngine
from .optimizer.param_store import get_params, update_params

router = APIRouter(prefix="/optimizer", tags=["optimizer"])
ENG = OptimizerEngine()


@router.post("/run/{strategy_id}")
def run_opt(strategy_id: str):
    return ENG.try_optimize(strategy_id)


@router.get("/params/{strategy_id}")
def get(strategy_id: str):
    return get_params(strategy_id)


@router.post("/params/{strategy_id}")
def set_params(strategy_id: str, body: dict):
    update_params(strategy_id, body)
    return {"ok": True}


