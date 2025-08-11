from fastapi import APIRouter
from typing import Dict, List
from .sizing.engine import dynamic_sl_and_lot, calc_lot_size

router = APIRouter(prefix="/sizing", tags=["sizing"])


@router.post("/dynamic")
def dynamic(body: Dict):
    symbol = body.get("symbol")
    side = body.get("side")
    entry = float(body.get("entry"))
    balance = float(body.get("balance"))
    point = float(body.get("point"))
    point_value = float(body.get("point_value"))
    high = body.get("high", [])
    low = body.get("low", [])
    close = body.get("close", [])
    sl, lots = dynamic_sl_and_lot(symbol, side, entry, balance, point, point_value, high, low, close)
    return {"sl": sl, "lots": lots}


@router.post("/calc")
def calc(body: Dict):
    return {
        "lots": calc_lot_size(
            float(body.get("balance")),
            float(body.get("risk_percent")),
            float(body.get("entry")),
            float(body.get("sl")),
            float(body.get("point")),
            float(body.get("point_value")),
            float(body.get("min_lot", 0.01)),
            float(body.get("max_lot", 5.0)),
        )
    }


