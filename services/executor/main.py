from __future__ import annotations

import os
import time
from typing import Any, Dict, Literal, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


EXEC_MODE: Literal["oanda", "mt5"] = os.getenv("EXEC_MODE", "oanda").lower()  # default: oanda
OANDA_API_KEY = os.getenv("OANDA_API_KEY", "")
OANDA_ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID", "")
OANDA_ENV = os.getenv("OANDA_ENV", "practice")


app = FastAPI(title="AIVO Executor API")


# ------------------------------ Models -------------------------------------


class PlaceOrderBody(BaseModel):
    symbol: str = Field(alias="instrument")
    side: Literal["buy", "sell"]
    units: int
    entryType: Literal["market", "limit"] = "market"
    limitPrice: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None


class CloseOrderBody(BaseModel):
    orderId: str


class RiskPositionSizeBody(BaseModel):
    balance: float
    riskPct: float
    slPips: float


def json_error(message: str, broker: Optional[dict] = None, status_code: int = 400):
    raise HTTPException(status_code=status_code, detail={"error": message, "broker": broker or {}})


# -------------------------- Broker: OANDA v20 -------------------------------


class OandaClient:
    def __init__(self, token: str, account: str, environment: str):
        try:
            from oandapyV20 import API  # type: ignore
            import oandapyV20.endpoints.orders as orders  # type: ignore
            import oandapyV20.endpoints.accounts as accounts  # type: ignore
            import oandapyV20.endpoints.positions as positions  # type: ignore
        except Exception as e:  # pragma: no cover
            json_error("oandapyV20 not installed", status_code=500, broker={"import_error": str(e)})
        self.API = API
        self.orders = orders
        self.accounts = accounts
        self.positions = positions
        self.api = API(access_token=token, environment=environment)
        self.account = account

    def health(self) -> Dict[str, Any]:
        try:
            req = self.accounts.AccountDetails(self.account)
            resp = self.api.request(req)
            return {"ok": True, "account": resp.get("account", {}).get("id")}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def place_order(self, body: PlaceOrderBody) -> Dict[str, Any]:
        order_payload: Dict[str, Any]
        if body.entryType == "market":
            order_payload = {
                "order": {
                    "units": str(body.units if body.side == "buy" else -abs(body.units)),
                    "instrument": body.symbol,
                    "timeInForce": "FOK",
                    "type": "MARKET",
                    "positionFill": "DEFAULT",
                }
            }
        else:
            if body.limitPrice is None:
                json_error("limitPrice required for entryType=limit")
            order_payload = {
                "order": {
                    "price": f"{body.limitPrice:.5f}",
                    "units": str(body.units if body.side == "buy" else -abs(body.units)),
                    "instrument": body.symbol,
                    "timeInForce": "GTC",
                    "type": "LIMIT",
                    "positionFill": "DEFAULT",
                }
            }
        if body.tp is not None:
            order_payload["order"]["takeProfitOnFill"] = {"price": f"{body.tp:.5f}"}
        if body.sl is not None:
            order_payload["order"]["stopLossOnFill"] = {"price": f"{body.sl:.5f}"}

        try:
            req = self.orders.OrderCreate(self.account, data=order_payload)
            resp = self.api.request(req)
            return resp
        except Exception as e:
            json_error("broker_error", broker={"request": order_payload, "error": str(e)}, status_code=502)

    def list_orders(self) -> Dict[str, Any]:
        try:
            req = self.orders.OrdersList(self.account)
            return self.api.request(req)
        except Exception as e:
            json_error("broker_error", broker={"error": str(e)}, status_code=502)

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        try:
            req = self.orders.OrderCancel(self.account, orderID=order_id)
            return self.api.request(req)
        except Exception as e:
            json_error("broker_error", broker={"orderId": order_id, "error": str(e)}, status_code=502)

    def positions(self) -> Dict[str, Any]:
        try:
            req = self.positions.OpenPositions(self.account)
            return self.api.request(req)
        except Exception as e:
            json_error("broker_error", broker={"error": str(e)}, status_code=502)


# -------------------------- Broker: MT5 bridge (stub) -----------------------


class MT5Client:
    """Document interfaces; actual implementation would wrap MetaTrader5 module.

    Methods mirror OandaClient: health, place_order, list_orders, cancel_order, positions.
    """

    def health(self) -> Dict[str, Any]:  # pragma: no cover - stub
        return {"ok": False, "error": "mt5_bridge_not_configured"}

    def place_order(self, body: PlaceOrderBody) -> Dict[str, Any]:  # pragma: no cover - stub
        json_error("mt5_bridge_not_implemented", status_code=501)

    def list_orders(self) -> Dict[str, Any]:  # pragma: no cover - stub
        json_error("mt5_bridge_not_implemented", status_code=501)

    def cancel_order(self, order_id: str) -> Dict[str, Any]:  # pragma: no cover - stub
        json_error("mt5_bridge_not_implemented", status_code=501)

    def positions(self) -> Dict[str, Any]:  # pragma: no cover - stub
        json_error("mt5_bridge_not_implemented", status_code=501)


def get_broker():
    if EXEC_MODE == "oanda":
        return OandaClient(OANDA_API_KEY, OANDA_ACCOUNT_ID, OANDA_ENV)
    return MT5Client()


# ------------------------------ Endpoints -----------------------------------


@app.get("/health")
def health():
    broker = get_broker()
    b = broker.health()
    return {"status": ("ok" if b.get("ok") else "degraded"), "broker": b}


@app.post("/orders/place")
def orders_place(body: PlaceOrderBody):
    broker = get_broker()
    return broker.place_order(body)


@app.get("/orders")
def orders_list():
    broker = get_broker()
    return broker.list_orders()


@app.post("/orders/close")
def orders_close(body: CloseOrderBody):
    broker = get_broker()
    return broker.cancel_order(body.orderId)


@app.get("/positions")
def positions():
    broker = get_broker()
    return broker.positions()


@app.post("/risk/position-size")
def risk_position_size(body: RiskPositionSizeBody):
    # Approx: $10 per pip per 100k units -> 0.0001 USD per pip per unit
    risk_amount = body.balance * (body.riskPct / 100.0)
    pip_value_per_unit = 0.0001
    if body.slPips <= 0:
        json_error("slPips must be > 0")
    units = int(max(1, round(risk_amount / (body.slPips * pip_value_per_unit))))
    return {"units": units}


@app.get("/schedule/allowed-now")
def schedule_allowed_now():
    # Simple time-window based on local or a TZ env
    from datetime import datetime, time as dtime
    try:
        from zoneinfo import ZoneInfo  # Python 3.9+
    except Exception:  # pragma: no cover
        ZoneInfo = None  # type: ignore

    tzname = os.getenv("TZ_SCHEDULE", "Asia/Ulaanbaatar")
    start = os.getenv("SCHEDULE_START", "09:00")
    end = os.getenv("SCHEDULE_END", "17:00")
    try:
        s_hour, s_min = [int(x) for x in start.split(":")]
        e_hour, e_min = [int(x) for x in end.split(":")]
    except Exception:
        s_hour, s_min, e_hour, e_min = 9, 0, 17, 0

    tz = ZoneInfo(tzname) if ZoneInfo else None
    now = datetime.now(tz) if tz else datetime.now()
    now_t = dtime(now.hour, now.minute)
    window = (dtime(s_hour, s_min), dtime(e_hour, e_min))
    allowed = window[0] <= now_t <= window[1]
    return {"allowed": allowed, "now": now.isoformat(), "window": {"start": start, "end": end, "tz": tzname}}

