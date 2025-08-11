from fastapi import APIRouter
from .routing.smart_router import SmartRouter
from .adapters.interfaces import OrderRequest

router = APIRouter(prefix="/routing", tags=["routing"])
SR = SmartRouter()


@router.post("/place")
def place(body: dict):
    req = OrderRequest(
        symbol=body["symbol"],
        side=body["side"],
        volume=float(body.get("volume", 0.01)),
        entry=float(body.get("entry")),
        sl=float(body.get("sl")),
        tp=float(body.get("tp")),
        comment=str(body.get("comment", "")),
    )
    outcomes = SR.route_order(body.get("oid") or f"{req.symbol}-{req.side}", req)
    return {"outcomes": outcomes}


