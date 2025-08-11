import statistics as st


def fit_queue(exec_rows):
    lats = [r["lat"] or 0 for r in exec_rows if (r["lat"] or 0) > 0]
    slips = [float(r["slip"] or 0) for r in exec_rows]
    if len(lats) < 20:
        return {"queue_init_depth": 8, "arrival_rate_lambda": 22.0, "cancel_rate_mu": 0.18, "aggress_ratio": 0.42}
    lat_avg = st.mean(lats)
    lat_p95 = sorted(lats)[int(0.95 * (len(lats) - 1))]
    slip_med = st.median(slips) if slips else 3.0
    depth = max(4, min(20, int((lat_avg / 120.0) * 8 + (slip_med / 5.0))))
    lam = max(8.0, min(60.0, 22.0 * (200.0 / max(80.0, lat_p95))))
    mu = max(0.05, min(0.6, 0.18 * (lat_avg / 300.0 + 0.8)))
    aggress = max(0.2, min(0.8, 0.42 * (1.0 + (slip_med / 10.0))))
    return {
        "queue_init_depth": depth,
        "arrival_rate_lambda": round(lam, 2),
        "cancel_rate_mu": round(mu, 2),
        "aggress_ratio": round(aggress, 2),
    }


