from fastapi import APIRouter
from .utils.tuner_db import last_accepted
from .tuner import run_once
import os

router = APIRouter(prefix="/tuner", tags=["tuner"])


@router.post("/run")
def run_tuner_once():
  return run_once()


@router.get("/status")
def tuner_status():
  return {"last_accepted": last_accepted(), "cooldown_active": os.path.exists("tuner.cooldown")}


