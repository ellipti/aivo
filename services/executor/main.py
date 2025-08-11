from __future__ import annotations

"""
Local run

  uvicorn services.executor.main:app --host 0.0.0.0 --port 7002 --reload
"""

import os
from datetime import datetime, time as dtime
from typing import Any, Dict, Literal, Optional

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


MODE: Literal["oanda", "mt5"] = os.getenv("MODE", "oanda").lower()  # default: oanda
OANDA_API_KEY = os.getenv("OANDA_API_KEY", "")
OANDA_ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID", "")
OANDA_ENV = os.getenv("OANDA_ENV", "practice")  # or live


app = FastAPI(title="AIVO Executor API")


class PlaceOrderBody(BaseModel):
  symbol: str = Field(alias="instrument")
  side: Literal["BUY", "SELL"]
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


def error_502(message: str, broker: Optional[dict] = None) -> HTTPException:
  return HTTPException(status_code=502, detail={"error": True, "message": message, "broker": broker or {}})


# -------------------------- Broker: OANDA v20 -------------------------------


def oanda_base_url() -> str:
  return "https://api-fxpractice.oanda.com/v3" if OANDA_ENV == "practice" else "https://api-fxtrade.oanda.com/v3"


def oanda_headers() -> Dict[str, str]:
  return {"Authorization": f"Bearer {OANDA_API_KEY}", "Content-Type": "application/json"}


async def oanda_health() -> Dict[str, Any]:
  try:
    url = f"{oanda_base_url()}/accounts/{OANDA_ACCOUNT_ID}"
    async with httpx.AsyncClient(timeout=15) as client:
      r = await client.get(url, headers=oanda_headers())
      ok = r.status_code == 200
      data = r.json() if r.content else {}
      return {"ok": ok, "account": data.get("account", {}).get("id")}
  except Exception as e:
    return {"ok": False, "error": str(e)}


async def oanda_place_order(body: PlaceOrderBody) -> Dict[str, Any]:
  order: Dict[str, Any]
  if body.entryType == "market":
    order = {
      "order": {
        "type": "MARKET",
        "timeInForce": "FOK",
        "instrument": body.symbol,
        "units": str(body.units if body.side == "BUY" else -abs(body.units)),
        "positionFill": "DEFAULT",
      }
    }
  else:
    if body.limitPrice is None:
      raise error_502("limitPrice required for limit orders")
    order = {
      "order": {
        "type": "LIMIT",
        "timeInForce": "GTC",
        "price": f"{body.limitPrice:.5f}",
        "instrument": body.symbol,
        "units": str(body.units if body.side == "BUY" else -abs(body.units)),
        "positionFill": "DEFAULT",
      }
    }
  if body.tp is not None:
    order["order"]["takeProfitOnFill"] = {"price": f"{body.tp:.5f}"}
  if body.sl is not None:
    order["order"]["stopLossOnFill"] = {"price": f"{body.sl:.5f}"}

  try:
    url = f"{oanda_base_url()}/accounts/{OANDA_ACCOUNT_ID}/orders"
    async with httpx.AsyncClient(timeout=30) as client:
      r = await client.post(url, headers=oanda_headers(), json=order)
      if r.status_code >= 400:
        raise error_502("broker_error", r.json())
      return r.json()
  except HTTPException:
    raise
  except Exception as e:
    raise error_502("request_failed", {"error": str(e), "request": order})


async def oanda_list_orders() -> Dict[str, Any]:
  try:
    url = f"{oanda_base_url()}/accounts/{OANDA_ACCOUNT_ID}/orders"
    async with httpx.AsyncClient(timeout=30) as client:
      r = await client.get(url, headers=oanda_headers())
      if r.status_code >= 400:
        raise error_502("broker_error", r.json())
      return r.json()
  except HTTPException:
    raise
  except Exception as e:
    raise error_502("request_failed", {"error": str(e)})


async def oanda_cancel_order(order_id: str) -> Dict[str, Any]:
  try:
    url = f"{oanda_base_url()}/accounts/{OANDA_ACCOUNT_ID}/orders/{order_id}/cancel"
    async with httpx.AsyncClient(timeout=30) as client:
      r = await client.put(url, headers=oanda_headers())
      if r.status_code >= 400:
        raise error_502("broker_error", r.json())
      return r.json()
  except HTTPException:
    raise
  except Exception as e:
    raise error_502("request_failed", {"error": str(e)})


async def oanda_positions() -> Dict[str, Any]:
  try:
    url = f"{oanda_base_url()}/accounts/{OANDA_ACCOUNT_ID}/openPositions"
    async with httpx.AsyncClient(timeout=30) as client:
      r = await client.get(url, headers=oanda_headers())
      if r.status_code >= 400:
        raise error_502("broker_error", r.json())
      return r.json()
  except HTTPException:
    raise
  except Exception as e:
    raise error_502("request_failed", {"error": str(e)})


# ------------------------------ Endpoints -----------------------------------


@app.get("/health")
async def health():
  return {"status": "ok", "mode": MODE}


@app.post("/orders/place")
async def orders_place(body: PlaceOrderBody):
  payload = await oanda_place_order(body)
  return payload


@app.get("/orders")
async def orders_list():
  return await oanda_list_orders()


@app.post("/orders/close")
async def orders_close(body: CloseOrderBody):
  return await oanda_cancel_order(body.orderId)


@app.get("/positions")
async def positions():
  return await oanda_positions()


@app.post("/risk/position-size")
async def risk_position_size(body: RiskPositionSizeBody):
  risk_amount = body.balance * (body.riskPct / 100.0)
  pip_value_per_unit = 0.0001
  if body.slPips <= 0:
    raise HTTPException(status_code=400, detail={"error": True, "message": "slPips must be > 0"})
  units = int(max(1, round(risk_amount / (body.slPips * pip_value_per_unit))))
  return {"units": units}


@app.get("/schedule/allowed-now")
async def schedule_allowed_now():
  try:
    from zoneinfo import ZoneInfo
  except Exception:
    ZoneInfo = None  # type: ignore
  tzname = os.getenv("TZ_SCHEDULE", "Asia/Ulaanbaatar")
  start = os.getenv("SCHEDULE_START", "09:00")
  end = os.getenv("SCHEDULE_END", "17:00")
  s_hour, s_min = [int(x) for x in start.split(":")]
  e_hour, e_min = [int(x) for x in end.split(":")]
  tz = ZoneInfo(tzname) if ZoneInfo else None
  now = datetime.now(tz) if tz else datetime.now()
  now_t = dtime(now.hour, now.minute)
  window = (dtime(s_hour, s_min), dtime(e_hour, e_min))
  allowed = window[0] <= now_t <= window[1]
  return {"allowed": allowed, "now": now.isoformat(), "window": {"start": start, "end": end, "tz": tzname}}

