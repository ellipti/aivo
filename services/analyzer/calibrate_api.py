from fastapi import APIRouter
import subprocess

router = APIRouter(prefix="/calibrate", tags=["calibrate"])


@router.post("/run")
def run_calibration():
  p = subprocess.run(["python", "services/analyzer/calibrate.py"], capture_output=True, text=True)
  ok = (p.returncode == 0)
  return {"ok": ok, "stdout": p.stdout, "stderr": p.stderr}


