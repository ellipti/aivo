from fastapi import APIRouter, Query
import json
from .journal.analytics import kpis, by_strategy, export_csv

CFG = json.load(open("configs/journal.json", "r", encoding="utf-8"))

router = APIRouter(prefix="/journal", tags=["journal"])


@router.get("/kpis")
def get_kpis(days: int | None = Query(default=None)):
    return kpis(last_days=days)


@router.get("/by-strategy")
def get_by_strategy():
    return {"items": by_strategy()}


@router.post("/export/csv")
def export():
    path = CFG["export_dir"] + CFG["csv_filename"]
    export_csv(path)
    return {"ok": True, "path": path}


