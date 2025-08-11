from fastapi import APIRouter, Query
from .utils.pnl import kpis, equity_series, daily_pnl

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/kpis")
def get_kpis():
    return kpis()


@router.get("/equity")
def get_equity(start_balance: float = Query(10000.0), risk_pct: float = Query(1.0)):
    return equity_series(start_balance=start_balance, risk_per_trade_pct=risk_pct)


@router.get("/daily")
def get_daily():
    return daily_pnl()


