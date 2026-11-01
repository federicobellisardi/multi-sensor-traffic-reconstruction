#!/usr/bin/env python3
"""Calibration of the demand on the detectors (Part A, step 1), with uncertainty.

Replaces the single-day choice of one factor k (demand_scan_eval.py) by:
  * a finer grid of global factors k on two calibration days (a Monday and a Saturday of February 2020);
  * "drop-one-class" runs at the current k: each demand class (CLASSES in demand_scaling.py) set to zero in
    turn, which gives the marginal contribution of every class to the flow on every detector link and
    shows how additive the classes are;
  * evaluation only on the calibration half of the 2020 detectors (same split and seed as
    demand_scan_eval.py); the other half, the 2021 campaign and the GPS data are never used here;
  * loss = mean squared log10(sim/obs) of the daily volumes per detector and day, each detector weighted by
    the share of its simulated flow that comes from the OD classes (scr_dest, scr_dest_prov), computed from the
    drop-one-class runs (simulated quantities only, never the observed counts); the unweighted loss and a
    hard selection (detectors above the median weight) are reported as sensitivity; a percentile
    bootstrap over detectors gives an interval for k*; 5-fold cross-validation over detectors
    (20 repeats) compares the best global k with a per-class linear model (non-negative weighted least
    squares on the class contributions). The per-class model assumes additivity, so a candidate run with its
    factors ("cand") must be simulated and evaluated before it is adopted.

  python3 calibrate_demand.py jobs            list the simulations (name, day) not yet done
  python3 calibrate_demand.py one NAME DAY    one simulation (cluster job); NAME is kX.X, drop_<class> or cand
  python3 calibrate_demand.py evaluate        -> model/results/demand/calibration.json, calibration_curve.csv
Outputs of the simulations: $SIM_RUNS/calibration/<name>/ (the k of k_calibration_base, at the two days, is one of the grid runs
from the k grid, where it is the member k_calibration_base).
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import nnls

sys.path.insert(0, str(Path(__file__).resolve().parent))
import demand_scaling as D  # noqa: E402
import demand_scan_eval as E  # noqa: E402
import reconstruct_and_validate as P  # noqa: E402

CAL_DAYS = ["2020-02-10", "2020-02-15"]
GRID = [0.6, 0.8, 1.0, 1.2, 1.5, 1.8, 2.2]  # includes k_calibration_base; wide because the LOCALS source moves vehicles since the minimocas fix
BASE = D.RUNS / "calibration"
FOLDS, REPEATS, N_BOOT, SEED = 5, 20, 2000, 20261031


def k0():
    """k of the base simulations (a member of GRID, simulated like the others); the drop-one-class runs use it.
    The k adopted for the final runs is k_choice.json['k']."""
    c = json.load(open(D.RES / "k_choice.json"))
    return c.get("k_calibration_base", c["k"])


def spec(name):
    """Class factors of a named simulation."""
    if name.startswith("drop_"):
        return {c: (0.0 if c == name[5:] else k0()) for c in D.CLASSES}
    if name == "cand":
        return json.load(open(D.RES / "class_factors.json"))["factors"]
    return {c: float(name[1:]) for c in D.CLASSES}


def basename(name, day):
    return BASE / name / f"sim_{D.tag(day)}"


def names():
    return [f"k{k:.1f}" for k in GRID] + [f"drop_{c}" for c in D.CLASSES]


def done(name, day):
    return bool(list(basename(name, day).parent.glob(f"sim_{D.tag(day)}_uniq_*.csv")))


def jobs():
    for day in CAL_DAYS:
        for name in names():
            if not done(name, day):
                print(name, day)


def one(name, day):
    base = basename(name, day)
    res = D.run(D.v6_config(day, D.VARIANTS["V6_scaled"], D.scaled_sources(day, spec(name)), base), base)
    print(*res, flush=True)
    sys.exit(1 if res[1] else 0)


def flows(name, day):
    if name == "base":
        name = f"k{k0():.1f}"
    d = basename(name, day).parent
    return D.link_daily(next(d.glob(f"sim_{D.tag(day)}_uniq_*.csv")))


def load(names_):
    o = D.group_observations()
    u = o.drop_duplicates("coil").reset_index(drop=True)
    calib = set(u.coil[E.split(u)])  # split of the detectors of either group, stratified by province
    o = o[o.coil.isin(calib)].reset_index(drop=True)
    cols = {}
    for n in names_:
        cols[n] = np.array([flows(n, d).get(l, 0.0) for d, l in o[["day", "poly_lid"]].values])
    return o, cols


def loss(obs, sim):
    return np.log10(np.clip(sim, 1, None) / obs)


OD_CLASSES = ["scr_dest", "scr_dest_prov"]  # classes with explicit origin-destination pairs


def od_weights(o, cols):
    """Weight of every detector: share of its simulated flow that comes from the OD classes (mean over the days).
    Built from simulated flows only (base minus drop-one-class runs), never from the observed counts."""
    base = cols["base"]
    od = sum(base - cols[f"drop_{c}"] for c in OD_CLASSES)
    share = np.clip(od / np.clip(base, 1, None), 0.0, 1.0)
    return pd.Series(share).groupby(o.coil.values).mean()


def evaluate():
    P.prepare_coils()
    kvals = sorted(set(GRID + [k0()]))
    nm = {k: ("base" if k == k0() else f"k{k:.1f}") for k in kvals}
    o, cols = load(list(nm.values()) + [f"drop_{c}" for c in D.CLASSES])
    obs = o.obs.values
    coil = o.coil.values
    ucoil = np.unique(coil)
    wc = od_weights(o, cols)
    w = wc.reindex(coil).values
    hard = w >= np.median(wc.values)  # sensitivity: only the detectors above the median OD share
    n_eff = float(wc.sum() ** 2 / (wc ** 2).sum())
    sq = np.array([loss(obs, cols[nm[k]]) ** 2 for k in kvals])  # (k, rows)
    wloss = lambda rows: (sq[:, rows] * w[rows]).sum(axis=1) / w[rows].sum()
    curve = pd.DataFrame({"k": kvals,
                          "weighted_mean_sq_log10": wloss(np.arange(len(obs))),
                          "mean_sq_log10": sq.mean(axis=1),
                          "median_abs_log10": [float(np.median(np.abs(loss(obs, cols[nm[k]])))) for k in kvals],
                          "volume_ratio": [float(cols[nm[k]].sum() / obs.sum()) for k in kvals]})
    curve.to_csv(D.RES / "calibration_curve.csv", index=False)

    rng = np.random.default_rng(SEED)
    idx_by_coil = {c: np.where(coil == c)[0] for c in ucoil}
    best = {"weighted": [], "unweighted": []}
    for _ in range(N_BOOT):
        rows = np.concatenate([idx_by_coil[c] for c in rng.choice(ucoil, len(ucoil))])
        best["weighted"].append(kvals[int(np.argmin(wloss(rows)))])
        best["unweighted"].append(kvals[int(np.argmin(sq[:, rows].mean(axis=1)))])
    all_rows = np.arange(len(obs))
    k_star = {"weighted": kvals[int(np.argmin(wloss(all_rows)))], "unweighted": kvals[int(np.argmin(sq.mean(axis=1)))],
              "hard_selection": kvals[int(np.argmin(sq[:, hard].mean(axis=1)))]}

    # class contributions at the current k and additivity
    base = cols["base"]
    contrib = np.column_stack([base - cols[f"drop_{c}"] for c in D.CLASSES])
    share = {c: float(contrib[:, i].sum() / base.sum()) for i, c in enumerate(D.CLASSES)}
    additivity = float(contrib.sum() / base.sum())

    # cross-validation over detectors: weighted loss on the held-out detectors
    def fit(rows):
        sw = np.sqrt(w[rows]) / np.sqrt(obs[rows])
        f, _ = nnls(contrib[rows] * sw[:, None], obs[rows] * sw)
        return f
    cv = {"best_global_k_weighted": [], "current_k": [], "per_class_linear_weighted": []}
    for r in range(REPEATS):
        perm = np.random.default_rng(SEED + r).permutation(ucoil)
        for f in range(FOLDS):
            test = np.concatenate([idx_by_coil[c] for c in perm[f::FOLDS]])
            train = np.setdiff1d(all_rows, test)
            kb = kvals[int(np.argmin(wloss(train)))]
            tl = lambda sim: float(np.sum(w[test] * loss(obs[test], sim) ** 2) / w[test].sum()) if w[test].sum() > 0 else float('nan')
            cv["best_global_k_weighted"].append(tl(cols[nm[kb]][test]))
            cv["current_k"].append(tl(base[test]))
            cv["per_class_linear_weighted"].append(tl(contrib[test] @ fit(train)))
    factors = fit(all_rows)
    out = {"calibration_days": CAL_DAYS, "calibration_coils": int(len(ucoil)), "rows": int(len(obs)),
           "k_current": k0(), "k_star": k_star, "od_classes": OD_CLASSES,
           "od_weight_quartiles": [float(x) for x in np.quantile(wc.values, [0, .25, .5, .75, 1])],
           "effective_number_of_detectors": n_eff,
           "k_star_bootstrap95": {m: [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))] for m, v in best.items()},
           "k_star_bootstrap_distribution": {m: {str(k): float(np.mean(np.array(v) == k)) for k in kvals} for m, v in best.items()},
           "class_share_of_flow_at_current_k": share, "additivity_sum_contrib_over_base": additivity,
           "class_factors_linear_model": dict(zip(D.CLASSES, map(float, factors))),
           "cv_weighted_mean_sq_log10": {k: [float(np.nanmean(v)), float(np.nanstd(v) / np.sqrt(np.sum(~np.isnan(v))))] for k, v in cv.items()},
           "cv_folds_with_positive_weight": float(np.mean(~np.isnan(cv["current_k"]))),
           "note": "weights = OD-class share of the simulated flow; per-class model assumes additive classes, "
                   "verify with a 'cand' run before adopting"}
    (D.RES / "calibration.json").write_text(json.dumps(out, indent=1) + "\n")
    (D.RES / "calibration_set.json").write_text(json.dumps(
        {"rule": "weight = share of simulated flow from " + "+".join(OD_CLASSES) + " (mean over " + ",".join(CAL_DAYS) + ")",
         "weights": {int(c): float(v) for c, v in wc.items()}}, indent=1) + "\n")
    (D.RES / "class_factors.json").write_text(json.dumps({"factors": out["class_factors_linear_model"],
                                                          "status": "candidate, unverified"}, indent=1) + "\n")
    print(curve.round(4).to_string(index=False))
    print(json.dumps({k: v for k, v in out.items() if k != "k_star_bootstrap_distribution"}, indent=1))


if __name__ == "__main__":
    cmd = sys.argv[1]
    {"jobs": jobs, "evaluate": evaluate}.get(cmd, lambda: one(*sys.argv[2:4]))()
