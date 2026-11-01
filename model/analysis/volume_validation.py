#!/usr/bin/env python3
"""Daily volumes of the final scaled simulations against detectors not used to choose the demand factor.

The factor k was chosen on a calibration half of the detectors of the February 2020 group means
(calibrate_demand.py, fixed seed). Here the simulated daily volume on the polyline of every other
detector is compared with its observed daily count (both directions), per detector and averaged over its
complete campaign days:
  * 2020 test: detectors outside the calibration half, all days of the campaign (10-17 Feb 2020);
  * 2021: all detectors, all days of the campaign (28 Jun - 4 Jul 2021).
Compared runs: V6_scaled (GPS-informed route choice) and V0_scaled (default distance route choice).
Statistics: Spearman rank correlation, simulated/observed volume ratio, median |log10(sim/obs)|, share
within a factor of 2; 95% bootstrap intervals over detectors (percentile, 2000 resamples, fixed seed), and
the paired V6 - V0 differences with the same bootstrap. For the detectors outside Forli-Cesena the same
statistics are given separately (route choice was selected on that province).

The same comparison is repeated on the group means of the test detectors (demand_scaling.group_observations).

Usage: python3 model/analysis/volume_validation.py      (SIM_RUNS as in demand_scaling.py)
Output: model/results/demand/volume_validation.json
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import demand_scaling as D  # noqa: E402
import demand_scan_eval as E  # noqa: E402
import reconstruct_and_validate as P  # noqa: E402

RUNS = {"V6": "V6_scaled", "V0": "V0_scaled"}
N_BOOT = 2000
SEED = 20261029
STATS = ["spearman", "ratio", "median_abs_log10", "within_factor2"]


def simulated(o, run):
    """Simulated daily volume of every observation row (coil, day), from the run of the day's weekday."""
    out = np.full(len(o), np.nan)
    cache = {}
    for i, (day, lid) in enumerate(o[["day", "poly_lid"]].values):
        if day not in cache:
            f = D.OUT / run / f"sim_{D.tag(day)}_uniq_{D.tag(day)}_000000.csv"
            cache[day] = D.link_daily(f)
        out[i] = cache[day].get(lid, 0.0)
    return out


def per_coil(o, sim):
    """Mean observed and simulated daily volume of every detector over its complete days."""
    z = o.assign(sim=sim).groupby(["coil", "prov"], as_index=False)[["obs", "sim"]].mean()
    return z[z.obs > 0].reset_index(drop=True)


def stats(z):
    return {k: v for k, v in E.scores(z.obs.values, z.sim.values).items() if k in STATS + ["n"]}


def bootstrap(z, extra=None):
    """Percentile intervals of the statistics (and of the paired differences if `extra` is given)."""
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, len(z), size=(N_BOOT, len(z)))
    draws = []
    for ix in idx:
        s = stats(z.iloc[ix])
        if extra is not None:
            t = stats(extra.iloc[ix])
            s = {k: s[k] - t[k] for k in STATS}
        draws.append(s)
    d = pd.DataFrame(draws)
    return {k: [float(d[k].quantile(0.025)), float(d[k].quantile(0.975))] for k in STATS}


def block(zs):
    """Statistics and intervals of one set of detectors for every run, plus the V6 - V0 difference."""
    res = {}
    for name, z in zs.items():
        res[name] = {**stats(z), "ci95": bootstrap(z)}
    if set(zs) == set(RUNS):
        a, b = zs["V6"], zs["V0"]
        assert (a.coil.values == b.coil.values).all()
        diff = {k: stats(a)[k] - stats(b)[k] for k in STATS}
        res["V6_minus_V0"] = {**diff, "ci95": bootstrap(a, b)}
    return res


def main():
    P.prepare_coils()  # links the 2020 detector table into SIM_RUNS/coils (as the assimilation step does)
    o = D.observations()
    g = D.group_observations()
    u = g.drop_duplicates("coil").reset_index(drop=True)
    calib = set(u.coil[E.split(u)])
    choice = json.load(open(D.RES / "k_choice.json"))
    assert len(calib) == choice["coils_calibration"], "calibration split differs from k_choice.json"

    sims = {name: simulated(o, run) for name, run in RUNS.items()}
    sets = {
        "2020_test": o.year.eq(2020) & ~o.coil.isin(calib),
        "2021_all": o.year.eq(2021),
    }
    out = {"k": choice["k"], "calibration_coils": len(calib), "n_bootstrap": N_BOOT, "bootstrap_seed": SEED}
    for key, m in sets.items():
        zs = {name: per_coil(o[m].reset_index(drop=True), s[m.values]) for name, s in sims.items()}
        out[key] = {"all": block(zs),
                    "outside_FC": block({n: z[z.prov != "FO"].reset_index(drop=True) for n, z in zs.items()}),
                    "n_coil_days": int(m.sum())}

    t = g[~g.coil.isin(calib)].reset_index(drop=True)
    zs = {name: per_coil(t, simulated(t, run)) for name, run in RUNS.items()}
    out["2020_test_groups"] = {"all": block(zs),
                               "outside_FC": block({n: z[z.prov != "FO"].reset_index(drop=True) for n, z in zs.items()}),
                               "n_coil_groups": int(len(t))}

    (D.RES / "volume_validation.json").write_text(json.dumps(out, indent=1) + "\n")
    for key in ("2020_test", "2020_test_groups", "2021_all"):
        for name in ("V6", "V0", "V6_minus_V0"):
            r = out[key]["all"][name]
            print(key, name, {k: round(r[k], 3) for k in STATS})


if __name__ == "__main__":
    main()
