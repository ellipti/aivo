from __future__ import annotations

import json
import itertools
import multiprocessing as mp
import csv

from .backtest_engine import load_csv, simulate_walk_forward, BtConfig
from .strategies.aivo_guarded import AIVOGuardedStrategy


def run_one(args):
    csv_path, guardrails_path, train, test, rr, minstop, max_conc = args
    candles = load_csv(csv_path)
    strat = AIVOGuardedStrategy(guardrails_path=guardrails_path, rr=rr, stop_pts_min=minstop)
    cfg = BtConfig(walk_train_bars=train, walk_test_bars=test, rr=rr, min_stop_pts=minstop, max_concurrent=max_conc)
    res = simulate_walk_forward(candles, cfg, strat)
    return {
        "train": train,
        "test": test,
        "rr": rr,
        "min_stop": minstop,
        "closed": res["closed_trades"],
        "hit_rate": res["hit_rate_pct"],
        "avg_r": res["avg_r"],
        "cum_r": res["cum_r"],
    }


def write_csv(rows, path):
    if not rows:
        return
    keys = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def render_html(rows, path):
    HEAD = """<!doctype html><html><head><meta charset="utf-8">
<title>AIVO Sweep Report</title>
<style>body{font:14px system-ui;margin:20px}
table{border-collapse:collapse;width:100%}th,td{padding:6px;border-bottom:1px solid #eee}
th{cursor:pointer;background:#fafafa}
.bad{color:#b91c1c}.good{color:#065f46}.med{color:#92400e}
</style></head><body><h1>Hyperparameter Sweep</h1>"""
    TAIL = """<script>
function sortTable(n){var t=document.getElementById("tbl"),r=true,s=0;while(r){r=false;var rows=t.rows;for(var i=1;i<rows.length-1;i++){var x=rows[i].getElementsByTagName("TD")[n];var y=rows[i+1].getElementsByTagName("TD")[n];var a=parseFloat(x.innerText)||x.innerText;var b=parseFloat(y.innerText)||y.innerText;var sw=false;if(s==0){if(a>b) sw=true;}else{if(a<b) sw=true;}if(sw){rows[i].parentNode.insertBefore(rows[i+1],rows[i]);r=true;break;}} if(!r && s==0){s=1;r=true;}}}
</script></body></html>"""
    cols = ["train", "test", "rr", "min_stop", "closed", "hit_rate", "avg_r", "cum_r"]
    rows_html = []
    for r in rows:
        cls_cum = "good" if r["cum_r"] > 0 else "bad"
        cls_hit = "good" if r["hit_rate"] >= 50 else ("med" if r["hit_rate"] >= 40 else "bad")
        rows_html.append(
            f"<tr><td>{r['train']}</td><td>{r['test']}</td><td>{r['rr']}</td><td>{r['min_stop']}</td>"
            f"<td>{r['closed']}</td><td class='{cls_hit}'>{r['hit_rate']}</td>"
            f"<td>{r['avg_r']}</td><td class='{cls_cum}'>{r['cum_r']}</td></tr>"
        )
    header = "<tr>" + "".join([f"<th onclick='sortTable({i})'>{c}</th>" for i, c in enumerate(cols)]) + "</tr>"
    html = HEAD + f"<table id='tbl'>{header}{''.join(rows_html)}</table>" + TAIL
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


if __name__ == "__main__":
    cfg = json.load(open("configs/sweep.json", "r", encoding="utf-8"))
    grid = list(itertools.product(cfg["train"], cfg["test"], cfg["rr"], cfg["min_stop_pts"]))
    tasks = [
        (cfg["csv_path"], cfg["guardrails_path"], tr, te, rr, ms, cfg["max_concurrent"]) for (tr, te, rr, ms) in grid
    ]

    workers = max(1, int(cfg.get("parallel_workers", mp.cpu_count() - 1)))
    with mp.Pool(processes=workers) as pool:
        rows = pool.map(run_one, tasks)

    rows.sort(key=lambda r: (r["cum_r"], r["hit_rate"], r["avg_r"]), reverse=True)
    write_csv(rows, cfg["out_csv"])
    render_html(rows, cfg["out_html"])
    print(f"Saved: {cfg['out_csv']} | {cfg['out_html']}")


