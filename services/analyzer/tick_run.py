import json
from .ticksim.run import run_once, run_mc

if __name__ == "__main__":
    cfg = json.load(open("configs/ticksim.json", "r", encoding="utf-8"))
    res = run_mc(cfg) if cfg.get("mc", {}).get("runs", 1) > 1 else run_once(cfg)
    print(json.dumps(res, ensure_ascii=False, indent=2))


