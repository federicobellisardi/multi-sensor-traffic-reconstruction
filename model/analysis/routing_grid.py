#!/usr/bin/env python3
"""Route-choice weights chosen on the detectors (Part A, step 2).

minimocas link cost = length * (alpha_we + alpha_speed * v_min / v + (1 - alpha_we - alpha_speed) * usage),
with v the link speed (GPS class speeds here) and usage a penalty on rarely used links (class weights of the
GPS counts). The current configuration V6 has alpha_we = 0.5, alpha_speed = 0, so the cost does not use speed.
Here a grid of (alpha_we, alpha_speed) is simulated with everything else fixed (final demand at the k of
k_choice.json, same route-choice files as V6) and compared on the calibration half of the 2020 detectors
(same split as demand_scan_eval.py) over two days, each detector weighted by the OD share of its simulated flow
(calibration_set.json, written by calibrate_demand.py evaluate, which must be run first). GPS data are not used for the choice, so that they remain an
independent validation set (step 5); the held-out half of the 2020 detectors and the 2021 campaign are not used
either.

Criteria: the route choice moves the volume level as well as its distribution, and k is re-estimated afterwards,
so variants are compared on level-free quantities: the Spearman correlation of daily volumes with the detectors
and the standard deviation of log10(sim/obs) over detector-days. Rule fixed before looking at the routing results: a
variant replaces V6 only if the paired bootstrap interval (over detectors, 2000 resamples, seed 20261032) of its improvement
excludes zero for the (unweighted) standard deviation (the OD-share weights turned out to be concentrated on ~6 effective
detectors, so the weighted sd is reported but not used for the decision); otherwise V6 is kept and the grid is reported as a sensitivity result.

  python3 routing_grid.py jobs            simulations still to run (name, day)
  python3 routing_grid.py one NAME DAY    one simulation (cluster job)
  python3 routing_grid.py evaluate        -> model/results/demand/routing_grid.json
V6 itself (w050_s000) is reused from the calibration run at the k of k_choice.json. Outputs of the runs: $SIM_RUNS/routing_grid/<name>/.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calibrate_demand as C  # noqa: E402
import demand_scaling as D  # noqa: E402
import reconstruct_and_validate as P  # noqa: E402

GRID = {"w100_s000": (1.0, 0.0), "w075_s025": (0.75, 0.25), "w050_s050": (0.5, 0.5), "w025_s075": (0.25, 0.75),
        "w000_s100": (0.0, 1.0), "w025_s025": (0.25, 0.25),
        "w050_s025": (0.5, 0.25)}  # added after the first grid: V6 distance term kept, plus travel time (usage weight 0.25)
REF = "w050_s000"  # V6
BASE = D.RUNS / "routing_grid"
N_BOOT, SEED = 2000, 20261032


def final_k():
    return json.load(open(D.RES / "k_choice.json"))["k"]


def basename(name, day):
    return BASE / name / f"sim_{D.tag(day)}"


def jobs():
    for day in C.CAL_DAYS:
        for name in GRID:
            if not list(basename(name, day).parent.glob(f"sim_{D.tag(day)}_uniq_*.csv")):
                print(name, day)


def one(name, day):
    we, sp = GRID[name]
    k = final_k()
    base = basename(name, day)
    cfg = D.v6_config(day, D.VARIANTS["V6_scaled"], D.scaled_sources(day, {c: k for c in D.CLASSES}), base)
    for s in cfg["sources"].values():
        for p in s.get("pawns", {}).values():
            p["alpha_we"], p["alpha_speed"] = we, sp
    res = D.run(cfg, base)
    print(*res, flush=True)
    sys.exit(1 if res[1] else 0)


def volumes(name, o):
    d = None
    out = np.zeros(len(o))
    cache = {}
    for i, (day, lid) in enumerate(o[["day", "poly_lid"]].values):
        if day not in cache:
            dd = C.basename(f"k{final_k():.1f}", day).parent if name == REF else basename(name, day).parent
            cache[day] = D.link_daily(next(dd.glob(f"sim_{D.tag(day)}_uniq_*.csv")))
        out[i] = cache[day].get(lid, 0.0)
    return out


def stats(o, sim):
    """sd of log10(sim/obs), unweighted and with the OD-share weights of calibrate_demand.py; Spearman; median."""
    r = np.log10(np.clip(sim, 1, None) / o.obs.values)
    w = o.w.values
    m = np.sum(w * r) / w.sum() if w.sum() > 0 else np.nan
    z = o.assign(sim=sim).groupby("coil")[["obs", "sim"]].mean()
    return {"sd_log10": float(np.std(r)),
            "sd_log10_weighted": float(np.sqrt(np.sum(w * (r - m) ** 2) / w.sum())) if w.sum() > 0 else float("nan"),
            "spearman": float(z.sim.corr(z.obs, method="spearman")), "median_log10_ratio": float(np.median(r))}


def evaluate():
    P.prepare_coils()
    names = [REF] + list(GRID)
    o, _ = C.load([])
    wf = D.RES / "calibration_set.json"
    assert wf.is_file(), "run calibrate_demand.py evaluate first (it writes the OD-share detector weights)"
    o["w"] = o.coil.map({int(k): v for k, v in json.load(open(wf))["weights"].items()}).values
    assert o.w.notna().all()
    sims = {n: volumes(n, o) for n in names}
    rng = np.random.default_rng(SEED)
    coils = o.coil.unique()
    by = {c: np.where(o.coil.values == c)[0] for c in coils}
    draws = [np.concatenate([by[c] for c in rng.choice(coils, len(coils))]) for _ in range(N_BOOT)]
    out = {"days": C.CAL_DAYS, "coils": int(len(coils)), "k": final_k(), "reference": REF, "variants": {}}
    for n in names:
        res = {"alpha_we": (0.5 if n == REF else GRID[n][0]), "alpha_speed": (0.0 if n == REF else GRID[n][1]),
               **stats(o, sims[n])}
        if n != REF:
            diffs = []
            for ix in draws:
                a, b = stats(o.iloc[ix], sims[n][ix]), stats(o.iloc[ix], sims[REF][ix])
                diffs.append((a["sd_log10"] - b["sd_log10"], a["spearman"] - b["spearman"],
                              a["sd_log10_weighted"] - b["sd_log10_weighted"]))
            d = np.array(diffs)
            res["sd_log10_weighted_minus_V6_ci95"] = [float(np.nanpercentile(d[:, 2], 2.5)), float(np.nanpercentile(d[:, 2], 97.5))]
            res["sd_log10_minus_V6_ci95"] = [float(np.percentile(d[:, 0], 2.5)), float(np.percentile(d[:, 0], 97.5))]
            res["spearman_minus_V6_ci95"] = [float(np.percentile(d[:, 1], 2.5)), float(np.percentile(d[:, 1], 97.5))]
            res["replaces_V6"] = bool(res["sd_log10_minus_V6_ci95"][1] < 0)
        out["variants"][n] = res
    (D.RES / "routing_grid.json").write_text(json.dumps(out, indent=1) + "\n")
    print(pd.DataFrame(out["variants"]).T.round(3).to_string())


if __name__ == "__main__":
    cmd = sys.argv[1]
    {"jobs": jobs, "evaluate": evaluate}.get(cmd, lambda: one(*sys.argv[2:4]))()
