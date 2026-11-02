#!/usr/bin/env python3
"""Radius of the random trip ends and k by day type, on the calibration detectors (group means).

  python3 radius_scan.py jobs            list the simulations not yet done (radius, k, day)
  python3 radius_scan.py one R K DAY     one simulation
  python3 radius_scan.py evaluate        first scan (radii 10, 20, 40) -> model/results/demand/radius_scan.json
  python3 radius_scan.py refine          refinement (15, 20, 25, 30 km)  -> model/results/demand/radius_scan_refined.json
Outputs: $SIM_RUNS/radius_scan/r<R>/k<K>/
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calibrate_demand as C  # noqa: E402
import demand_scaling as D  # noqa: E402

RADII = [10, 20, 40]
GRID = [0.6, 0.8, 1.0, 1.2, 1.5, 1.8]
BASE = D.RUNS / "radius_scan"
N_BOOT, SEED = 2000, 20261039


FINE = [float(x) for x in os.environ.get("K_GRID", "0.7,0.8,0.9,1.0,1.1,1.2").split(",")]  # refinement around the selected radius
PLAN = {r: FINE for r in (15, 20, 25, 30)}


def base(r, k, day):
    return BASE / f"r{r}" / f"k{k:.1f}" / f"sim_{D.tag(day)}"


def jobs():
    for r, grid in PLAN.items():
        for k in grid:
            for day in C.CAL_DAYS:
                if not list(base(r, k, day).parent.glob(f"sim_{D.tag(day)}_uniq_*.csv")):
                    print(r, k, day)


def one(r, k, day):
    r, k = int(r), float(k)
    b = base(r, k, day)
    c = D.v6_config(day, D.VARIANTS["V6_scaled"], D.scaled_sources(day, {x: k for x in D.CLASSES}), b)
    c["cherry_pick_mode"]["medium"] = float(r)
    res = D.run(c, b)
    print(*res, flush=True)
    sys.exit(1 if res[1] else 0)


def sd(sim, obs):
    return float(np.log10(np.clip(sim, 1, None) / obs).std())


def msq(sim, obs):
    return float((np.log10(np.clip(sim, 1, None) / obs) ** 2).mean())


def report(o, sim):
    obs = o.obs.values
    out = {"sd_log10": sd(sim, obs), "mean_sq_log10": msq(sim, obs), "ratio": float(sim.sum() / obs.sum()),
           "within_factor2": float(np.mean(np.abs(np.log10(np.clip(sim, 1, None) / obs)) < np.log10(2)))}
    for day in C.CAL_DAYS:
        m = (o.day == day).values
        out[day] = {"sd_log10": sd(sim[m], obs[m]), "mean_sq_log10": msq(sim[m], obs[m]), "ratio": float(sim[m].sum() / obs[m].sum()),
                    "spearman": float(spearmanr(obs[m], sim[m])[0]), "slope": float(np.polyfit(np.log10(obs[m]), np.log10(np.clip(sim[m], 1, None)), 1)[0])}
    return out


def paired(o, a, b):
    obs, coil = o.obs.values, o.coil.values
    u = np.unique(coil)
    idx = {c: np.where(coil == c)[0] for c in u}
    rng = np.random.default_rng(SEED)
    d = []
    for _ in range(N_BOOT):
        i = np.concatenate([idx[c] for c in rng.choice(u, len(u))])
        d.append(sd(a[i], obs[i]) - sd(b[i], obs[i]))
    ci = [float(x) for x in np.percentile(d, [2.5, 97.5])]
    return {"difference": sd(a, obs) - sd(b, obs), "ci95": ci, "below_zero": bool(ci[1] < 0)}


def refine():
    """Rule C: the best refined radius, each with k by day type, against 20 km at k = 1.0 / 0.8."""
    C.BASE = BASE / "r20"
    o, cols = C.load([f"k{k:.1f}" for k in FINE])
    obs = o.obs.values
    sims = {20: {k: cols[f"k{k:.1f}"] for k in FINE}}
    for r in (15, 25, 30):
        C.BASE = BASE / f"r{r}"
        _, cols = C.load([f"k{k:.1f}" for k in FINE])
        sims[r] = {k: cols[f"k{k:.1f}"] for k in FINE}
    days = {d: (o.day == d).values for d in C.CAL_DAYS}
    best = {r: {d: min(FINE, key=lambda k: msq(sims[r][k][m], obs[m])) for d, m in days.items()} for r in sims}
    bysim = {r: sum(sims[r][best[r][d]] * m for d, m in days.items()) for r in sims}
    ref = bysim[20] if D.NO_CODE else sims[20][1.0] * days[C.CAL_DAYS[0]] + sims[20][0.8] * days[C.CAL_DAYS[1]]
    r_best = min(sims, key=lambda r: msq(bysim[r], obs))
    k_common = min(FINE, key=lambda k: msq(sims[20][k], obs))
    out = {"k_by_day_type": best, "selected_radius": r_best, "reference_r20_k10_k08": report(o, ref),
           "by_radius": {r: report(o, bysim[r]) for r in sims},
           "loss_by_radius_day_k": {r: {d: {k: msq(sims[r][k][m], obs[m]) for k in FINE} for d, m in days.items()} for r in sims},
           "rule_C_selected_vs_r20": paired(o, bysim[r_best], ref),
           "r20_common_k": k_common, "r20_common_k_report": report(o, sims[20][k_common]),
           "r20_k_by_day_vs_common_k": paired(o, bysim[20], sims[20][k_common])}
    (D.RES / "radius_scan_refined.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


def evaluate():
    C.BASE = BASE / "r10"
    o, _ = C.load([f"k{k:.1f}" for k in GRID[:1]])
    obs = o.obs.values
    sims = {}
    for r in RADII:
        C.BASE = BASE / f"r{r}"
        _, cols = C.load([f"k{k:.1f}" for k in GRID])
        sims[r] = {k: cols[f"k{k:.1f}"] for k in GRID}
    days = {d: (o.day == d).values for d in C.CAL_DAYS}
    best = {r: {d: min(GRID, key=lambda k: msq(sims[r][k][m], obs[m])) for d, m in days.items()} for r in RADII}
    bysim = {r: sum(sims[r][best[r][d]] * m for d, m in days.items()) for r in RADII}
    common = min(GRID, key=lambda k: msq(sims[10][k], obs))
    r_best = min(RADII[1:], key=lambda r: msq(bysim[r], obs))
    out = {"detectors": int(o.coil.nunique()), "rows": int(len(o)), "k_by_day_type": best,
           "loss_by_radius_day_k": {r: {d: {k: msq(sims[r][k][m], obs[m]) for k in GRID} for d, m in days.items()} for r in RADII},
           "reference_k12_r10": report(o, sims[10][1.2]), "k_common_r10": common,
           "r10_k_by_day": report(o, bysim[10]), "by_radius": {r: report(o, bysim[r]) for r in RADII},
           "rule_A_k_by_day_vs_k12": paired(o, bysim[10], sims[10][1.2]),
           "selected_radius": r_best, "rule_B_radius_vs_10": paired(o, bysim[r_best], bysim[10])}
    (D.RES / "radius_scan.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    cmd = sys.argv[1]
    {"jobs": jobs, "evaluate": evaluate, "refine": refine}.get(cmd, lambda: one(*sys.argv[2:5]))()
