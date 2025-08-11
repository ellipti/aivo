import statistics as st


def fit_slippage_k(exec_rows, spread_pts_map, point):
    xs = []
    ys = []
    for r in exec_rows:
        t = (int(r["ts"]) // 60) * 60
        sp = spread_pts_map.get(t)
        if not sp:
            continue
        xs.append(sp)
        ys.append(float(r["slip"]))
    if len(xs) < 20:
        return {"k": 0.35, "fixed_pts": st.median(ys) if ys else 5}
    num = sum(x * y for x, y in zip(xs, ys))
    den = sum(x * x for x in xs) or 1.0
    k = max(0.05, min(1.5, num / den))
    med_sp = st.median(xs)
    fixed = st.median([y for x, y in zip(xs, ys) if x <= med_sp]) if ys else 3
    fixed = max(0.0, min(30.0, fixed))
    return {"k": round(k, 3), "fixed_pts": round(fixed, 2)}


def fit_latency(exec_rows):
    lats = [int(r["lat"] or 0) for r in exec_rows if (r["lat"] or 0) >= 0]
    if not lats:
        return {"avg": 0, "p95": 0, "cap": 800}
    avg = int(st.mean(lats))
    p95 = int(sorted(lats)[int(0.95 * (len(lats) - 1))])
    cap = max(300, min(2000, int(p95 * 1.1)))
    return {"avg": avg, "p95": p95, "cap": cap}


