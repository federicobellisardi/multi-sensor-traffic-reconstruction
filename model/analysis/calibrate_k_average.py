#!/usr/bin/env python3
"""Choice of the demand factor k on the long-term detector averages (data/coils_ave_*.csv).

The February 2020 detector days are noisy single observations of a few dozen detectors. The MTS average
files give, for every detector (275-288) and weekday, the average winter profile of 2022, 2023 and the first
quarter of 2024. Target of the calibration: the average winter daily volume (both directions, mean of the available
years) of the detector on the weekday of the simulated day (Monday for 2020-02-10, Saturday for 2020-02-15).
The simulations are those of calibrate_demand.py (global k grid and the k of V6_scaled).

Loss: mean squared log10(sim/target) over detector-days; percentile bootstrap over detectors (2000 resamples, seed
20261034) for k*. Independent checks: the same loss against the observed 2020-02-10 and 2020-02-15 volumes (the
period of the OD, not used here) and the level drift between the 2020 observations and the 2022-24 averages on the
detectors present in both (the averages are three to four years later than the OD).

  python3 calibrate_k_average.py          -> model/results/demand/calibration_average.json, calibration_average_curve.csv
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calibrate_demand as C  # noqa: E402
import demand_scaling as D  # noqa: E402
from paths import ROOT  # noqa: E402

FILES = ["coils_ave_220101-000000_221231-234500.csv", "coils_ave_230101-000000_231231-234500.csv",
         "coils_ave_240101-000000_240331-234500.csv"]
WDAY = {"2020-02-10": "Mon", "2020-02-15": "Sat"}
N_BOOT, SEED = 2000, 20261034


def targets():
    """Average winter daily volume per detector and weekday, mean over the years that have it."""
    bar = pd.read_csv(ROOT / "vars/extra/er_barriers_cartodata.csv", sep=";")
    lid = dict(zip(bar.tag.astype(int), bar.poly_lid.astype(int)))
    per_year = []
    for f in FILES:
        d = pd.read_csv(ROOT / "data" / f, sep=";")
        d = d[d.season == "winter"]
        tot = {}
        for wd in set(WDAY.values()):
            z = d[d.wday == wd]
            if len(z) != 96:
                continue
            for c in sorted({int(x.split("_")[0]) for x in z.columns if x[0].isdigit()}):
                cc = [f"{c}_0", f"{c}_1"]
                if all(x in z for x in cc) and z[cc].notna().all().all():
                    tot[(c, wd)] = float(z[cc].values.sum())
        per_year.append(pd.Series(tot))
    t = pd.concat(per_year, axis=1).mean(axis=1).rename("target").reset_index()
    t.columns = ["coil", "wday", "target"]
    t = t[t.coil.isin(lid) & (t.target > 0)]
    t["poly_lid"] = t.coil.map(lid)
    return t


def sim_flows(name, day):
    return C.flows(name, day)


def main():
    t = targets()
    kvals = sorted(set(C.GRID + [C.k0()]))
    nm = {k: ("base" if k == C.k0() else f"k{k:.1f}") for k in kvals}
    rows = []
    for day, wd in WDAY.items():
        z = t[t.wday == wd].copy()
        z["day"] = day
        for k in kvals:
            z[f"s{k}"] = z.poly_lid.map(sim_flows(nm[k], day)).fillna(0.0).values
        rows.append(z)
    z = pd.concat(rows, ignore_index=True)
    r = np.array([np.log10(np.clip(z[f"s{k}"].values, 1, None) / z.target.values) for k in kvals])
    sq = r ** 2
    curve = pd.DataFrame({"k": kvals, "mean_sq_log10": sq.mean(axis=1),
                          "median_abs_log10": np.median(np.abs(r), axis=1),
                          "median_log10_ratio": np.median(r, axis=1),
                          "volume_ratio": [float(z[f"s{k}"].sum() / z.target.sum()) for k in kvals]})
    coils = z.coil.unique()
    by = {c: np.where(z.coil.values == c)[0] for c in coils}
    rng = np.random.default_rng(SEED)
    best = []
    for _ in range(N_BOOT):
        rows_ = np.concatenate([by[c] for c in rng.choice(coils, len(coils))])
        best.append(kvals[int(np.argmin(sq[:, rows_].mean(axis=1)))])
    k_star = kvals[int(np.argmin(sq.mean(axis=1)))]
    # independent check against the observed 2020 days, and level drift
    o = D.group_observations()
    ro = np.array([np.log10(np.clip(np.array([sim_flows(nm[k], d).get(l, 0.0) for d, l in o[["day", "poly_lid"]].values]), 1, None) / o.obs.values) for k in kvals])
    curve["obs2020_mean_sq_log10"] = (ro ** 2).mean(axis=1)
    curve["obs2020_median_log10_ratio"] = np.median(ro, axis=1)
    m = o.assign(wday=o.day.map(WDAY)).merge(t[["coil", "wday", "target"]], on=["coil", "wday"])
    drift = float(np.median(np.log10(m.obs / m.target)))
    curve.to_csv(D.RES / "calibration_average_curve.csv", index=False)
    out = {"targets": "winter average 2022, 2023, 2024Q1 (data/coils_ave_*.csv)", "days": WDAY,
           "detectors": int(len(coils)), "detector_days": int(len(z)), "k_current": C.k0(), "k_star": k_star,
           "k_star_bootstrap95": [float(np.percentile(best, 2.5)), float(np.percentile(best, 97.5))],
           "k_star_bootstrap_distribution": {str(k): float(np.mean(np.array(best) == k)) for k in kvals},
           "obs2020_k_star": kvals[int(np.argmin((ro ** 2).mean(axis=1)))], "obs2020_detector_days": int(len(o)),
           "level_drift_obs2020_over_average_median_log10": drift, "level_drift_detectors": int(m.coil.nunique())}
    (D.RES / "calibration_average.json").write_text(json.dumps(out, indent=1) + "\n")
    print(curve.round(4).to_string(index=False))
    print(json.dumps({k: v for k, v in out.items() if k != "k_star_bootstrap_distribution"}, indent=1))


if __name__ == "__main__":
    main()
