from __future__ import annotations

"""
Local run (ATTACH-ONLY):

  uvicorn services.executor.main:app --host 0.0.0.0 --port 7002 --reload

Behavior: attaches to a running MT5 terminal session. It will NOT login with
credentials unless MT5_FORCE_LOGIN=true. If not authorized, trading endpoints
return 503 with reason mt5_not_authorized.
"""

import os
from datetime import datetime, time as dtime
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Literal

from . import mt5_adapter

# Load .env adjacent to this file
load_dotenv(dotenv_path=Path(__file__).with_name(".env"))

MODE = "mt5"
FORCE_LOGIN = os.getenv("MT5_FORCE_LOGIN", "false").lower() == "true"
MT5_PATH = os.getenv("MT5_PATH") or None
MT5_LOGIN = int(os.getenv("MT5_LOGIN")) if (os.getenv("MT5_LOGIN") and FORCE_LOGIN) else None
MT5_PASSWORD = os.getenv("MT5_PASSWORD") if FORCE_LOGIN else None
MT5_SERVER = os.getenv("MT5_SERVER") if FORCE_LOGIN else None


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


def init_state() -> Dict[str, Any]:
  return mt5_adapter.init_mt5(
      path=MT5_PATH,
      force_login=FORCE_LOGIN,
      login=MT5_LOGIN,
      password=MT5_PASSWORD,
      server=MT5_SERVER,
  )


def unauthorized_response() -> JSONResponse:
  return JSONResponse(status_code=503, content={
      "error": True,
      "reason": "mt5_not_authorized",
      "hint": "Open MT5 terminal, login to your account, then retry."
  })


# ------------------------------ Endpoints -----------------------------------


@app.get("/health")
async def health():
    state = init_state()
    return JSONResponse({
        "status": ("ok" if state.get("authorized") else state.get("status", "no_session")),
        "mode": MODE,
        "authorized": bool(state.get("authorized")),
        "terminal": state.get("terminal"),
        "account": state.get("account"),
        "server": state.get("server"),
    })


@app.post("/orders/place")
async def orders_place(body: PlaceOrderBody):
    state = init_state()
    if not state.get("authorized"):
        return unauthorized_response()
    data = mt5_adapter.place_order(body.model_dump(by_alias=True))
    return JSONResponse(data)


@app.get("/orders")
async def orders_list():
    state = init_state()
    if not state.get("authorized"):
        return unauthorized_response()
    data = mt5_adapter.list_orders()
    return JSONResponse(data)


@app.post("/orders/close")
async def orders_close(body: CloseOrderBody):
    state = init_state()
    if not state.get("authorized"):
        return unauthorized_response()
    data = mt5_adapter.close_order(body.orderId)
    return JSONResponse(data)


@app.get("/positions")
async def positions():
    state = init_state()
    if not state.get("authorized"):
        return unauthorized_response()
    data = mt5_adapter.list_positions()
    return JSONResponse(data)


@app.post("/risk/position-size")
async def risk_position_size(body: RiskPositionSizeBody):
  risk_amount = body.balance * (body.riskPct / 100.0)
  pip_value_per_unit = 0.0001
  if body.slPips <= 0:
    return JSONResponse(status_code=400, content={"error": True, "message": "slPips must be > 0"})
  units = int(max(1, round(risk_amount / (body.slPips * pip_value_per_unit))))
  return JSONResponse({"units": units})


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
  return JSONResponse({"allowed": allowed, "now": now.isoformat(), "window": {"start": start, "end": end, "tz": tzname}})

