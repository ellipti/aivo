from fastapi import APIRouter
from typing import Dict, List
from .risk.hedge_engine import recommend_hedges
from .risk.balancer import portfolio_risk_pct, need_deleveraging, open_trades

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/exposure")
def exposure():
    return {"portfolio_risk_pct": portfolio_risk_pct(), "need_deleveraging": need_deleveraging()}


@router.post("/hedge/recommend")
def hedge_recommend(body: Dict[str, List[float]]):
    # body: { "XAUUSD":[close...], "DXY":[close...], ... }
    return {"orders": recommend_hedges(body, open_trades())}


