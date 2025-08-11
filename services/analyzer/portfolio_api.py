from fastapi import APIRouter
from .utils.portfolio import current_risk_pct, per_symbol_open_count

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/exposure")
def exposure():
    return {"open_risk_pct": current_risk_pct(), "open_by_symbol": per_symbol_open_count()}


