from fastapi import APIRouter
import datetime as dt
from .news.feed import fetch_events, pre_news_pause
from .news.sentiment import analyze_text

router = APIRouter(prefix="/news", tags=["news"])


@router.get("/events")
def events():
    return {"items": fetch_events()}


@router.get("/guard")
def guard(symbol: str):
    return pre_news_pause(symbol, dt.datetime.now(dt.timezone.utc))


@router.post("/sentiment")
def sentiment(body: dict):
    text = str(body.get("text", ""))
    return analyze_text(text)


