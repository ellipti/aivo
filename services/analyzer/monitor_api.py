from fastapi import APIRouter
from .monitor.run_checks import run_checks
from .monitor.actions import is_paused

router = APIRouter(prefix="/monitor", tags=["monitor"])


@router.post("/scan")
def scan():
    return run_checks()


@router.get("/guard")
def guard():
    p, why = is_paused()
    return {"paused": p, "why": why}


