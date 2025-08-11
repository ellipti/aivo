from __future__ import annotations
import math


def ks_stat(sample_a, sample_b):
    if not sample_a or not sample_b:
        return 0.0
    a = sorted(sample_a)
    b = sorted(sample_b)
    ia = ib = 0
    na = len(a)
    nb = len(b)
    d = 0.0
    while ia < na and ib < nb:
        if a[ia] <= b[ib]:
            ia += 1
        else:
            ib += 1
        fa = ia / na
        fb = ib / nb
        d = max(d, abs(fa - fb))
    return d


def psi(ref, cur, bins=10):
    if not ref or not cur:
        return 0.0
    mn = min(min(ref), min(cur))
    mx = max(max(ref), max(cur))
    if mx <= mn:
        return 0.0
    w = (mx - mn) / bins
    eps = 1e-9

    def hist(x):
        h = [0] * bins
        for v in x:
            k = min(bins - 1, max(0, int((v - mn) / w)))
            h[k] += 1
        tot = max(1, sum(h))
        return [c / tot for c in h]

    pr = hist(ref)
    pc = hist(cur)
    val = 0.0
    for r, c in zip(pr, pc):
        r = max(r, eps)
        c = max(c, eps)
        val += (c - r) * math.log(c / r)
    return val


