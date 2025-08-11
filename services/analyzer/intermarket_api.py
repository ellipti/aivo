from fastapi import APIRouter
from typing import Dict, List
from .intermarket.correlation import evaluate as eval_corr
from .intermarket.regime import detect_regime

router = APIRouter(prefix="/intermarket", tags=["intermarket"])


@router.post("/correlation")
def correlation(payload: Dict[str, List[float]]):
    return eval_corr(payload)


@router.post("/regime/{symbol}")
def regime(symbol: str, body: Dict[str, List[float]]):
    close = body.get("close", [])
    high = body.get("high", [])
    low = body.get("low", [])
    r = detect_regime(close, high, low)
    return {"symbol": symbol, "regime": r}


