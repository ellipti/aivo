from fastapi import APIRouter
from .agents.swarm_coordinator import SwarmCoordinator

router = APIRouter(prefix="/swarm", tags=["swarm"])
COORD = SwarmCoordinator()


@router.post("/run")
def run_swarm(stats: dict):
    COORD.run_cycle({"stats": stats})
    return {"ok": True}


