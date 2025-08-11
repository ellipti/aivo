import csv, json, sys


def pareto_front(rows):
    front = []
    for i, r in enumerate(rows):
        dominated = False
        for j, s in enumerate(rows):
            if j == i:
                continue
            if (
                (s["cum_r"] >= r["cum_r"]
                 and s["hit_rate"] >= r["hit_rate"]
                 and s["avg_r"] >= r["avg_r"]) and
                (s["cum_r"] > r["cum_r"]
                 or s["hit_rate"] > r["hit_rate"]
                 or s["avg_r"] > r["avg_r"]) 
            ):
                dominated = True
                break
        if not dominated:
            front.append(r)
    return front


if __name__ == "__main__":
    inp = sys.argv[1] if len(sys.argv) > 1 else "sweep_results.csv"
    rows = []
    with open(inp, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append({
                k: (
                    float(v)
                    if k in ("rr", "min_stop", "closed", "hit_rate", "avg_r", "cum_r")
                    else int(v)
                    if k in ("train", "test")
                    else v
                )
                for k, v in r.items()
            })
    front = pareto_front(rows)
    front.sort(key=lambda r: (r["cum_r"], r["hit_rate"]), reverse=True)
    print(json.dumps(front[:10], ensure_ascii=False, indent=2))


