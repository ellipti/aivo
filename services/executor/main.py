from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="AIVO Executor API")


class Order(BaseModel):
    instrument: str
    units: int
    side: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/order")
def place_order(order: Order):
    # Stub: integrate OANDA v20 and MT5 bridge later
    return {"status": "accepted", "order": order}

