import json
from .backtest.engine import run_backtest

if __name__ == "__main__":
    cfg = json.load(open("configs/backtest.json", "r", encoding="utf-8"))
    s = run_backtest(cfg)
    print(json.dumps(s, ensure_ascii=False, indent=2))


