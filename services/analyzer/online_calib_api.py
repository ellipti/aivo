from fastapi import APIRouter
from .online_calib import run_once
import json, os

router = APIRouter(prefix="/calib", tags=["calibration"])


@router.post("/online/run")
def online_calib_run():
  return run_once()


@router.get("/online/report")
def online_calib_report():
  p = "online_calib_report.json"
  return json.load(open(p, "r", encoding="utf-8")) if os.path.exists(p) else {}


