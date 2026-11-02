#!/usr/bin/env python3
"""Why the error at single roads is large: decomposition of log10(simulated/observed) of daily volumes. Diagnostic, selects nothing.

Is the error of a detector persistent between day types and years; how large is the day-to-day noise of the counts; how much
road class, province and observed volume explain; does it change with the demand or with the routing; is it shared by
nearby detectors. Calibration half for the comparison between runs, all complete detectors for persistence between years.

  python3 single_road_error.py -> model/results/demand/single_road_error.json (run before the province factors; do not rerun:
      the 2021 persistence reads the current loo_detectors.csv)
  python3 single_road_error.py adopted -> model/results/demand/single_road_error_province.json (model with the factors)
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calibrate_demand as C  # noqa: E402
import demand_scaling as D  # noqa: E402
import detector_baselines as B  # noqa: E402
import od_matrix as M  # noqa: E402
import reconstruct_and_validate as P  # noqa: E402
import source_value as V  # noqa: E402
from paths import ROOT  # noqa: E402

MON, SAT = C.CAL_DAYS
RUNS = {"without_od_relations": lambda d: D.RUNS / "source_value/no_od", "N100": lambda d: M.OUT / "N100_r20_x_m1.15", "N347_with_code": lambda d: M.OUT / "N347_r20",
        "shortest_distance_routing": lambda d: D.RUNS / "demand_before_province/V0_scaled"}
BINS = [(0, 5), (5, 10), (10, 20), (20, 50), (50, 400)]
N_PERM, SEED = 5000, 20261048


def resid(t, path, day):
    q = t[t.day == day]
    return pd.Series(np.log10(np.clip(V.daily(path(day), day, q.poly_lid), 1, None) / q.obs.values), index=q.coil.values)


def r2(y, x):
    X = np.column_stack([np.ones(len(y)), x])
    return float(1 - ((y - X @ np.linalg.lstsq(X, y, rcond=None)[0]) ** 2).sum() / ((y - y.mean()) ** 2).sum())


def noise():
    """Log10 deviation of each weekday from the mean of the weekdays, per detector: what no daily model could predict."""
    obs = P.coil_table_local(2020)
    days = D.GROUPS[MON][0]
    z = obs[np.isin(obs.index.strftime("%Y-%m-%d"), days)]
    coils = sorted({c[:-2] for c in z.columns if c[-2:] == "_0" and c[:-2] + "_1" in z})
    out = []
    for c in coils:
        g = z[[c + "_0", c + "_1"]]
        v = g[g.notna().all(axis=1)].groupby(g[g.notna().all(axis=1)].index.strftime("%Y-%m-%d")).agg(["sum", "size"])
        v = v[c + "_0"]["sum"].where(v[c + "_0"]["size"] == 96) + v[c + "_1"]["sum"].where(v[c + "_1"]["size"] == 96)
        v = v.dropna()
        if len(v) >= 3 and (v > 0).all():
            out.append(np.log10(v / v.mean()).std())
    return float(np.median(out)), len(out)


def main(adopted=False):
    rng = np.random.default_rng(SEED)
    t = M.table("cal")
    all_t = D.group_observations()
    res = {}
    model = (lambda d: D.OUT / "V6_scaled") if adopted else M.frozen_path
    base = {d: resid(t, model, d) for d in C.CAL_DAYS}
    a = pd.concat([base[MON], base[SAT]], axis=1, keys=["m", "s"]).dropna()
    res["sd_log10"] = {"monday": float(base[MON].std()), "saturday": float(base[SAT].std())}
    res["persistence"] = {"monday_saturday": {"detectors": int(len(a)), "r": float(a.m.corr(a.s))}}
    full = pd.concat([resid(all_t, model, d) for d in (MON,)], axis=1, keys=["m"])
    l = pd.read_csv(D.R1 / "corrected/loo_detectors.csv").dropna(subset=["raw_total"]) if hasattr(D, "R1") else None
    l = l[l.day.str.startswith("2021")].groupby(["coil", "day"])[["obs_total", "raw_total"]].sum().groupby("coil").mean()
    l = np.log10(l.raw_total.clip(lower=1) / l.obs_total)
    b = pd.concat([full.m, l], axis=1, keys=["a", "b"]).dropna()
    res["persistence"]["winter_2020_summer_2021"] = {"detectors": int(len(b)), "r": float(b.a.corr(b.b))}
    n, k = noise()
    res["day_to_day_noise_log10_median"] = {"value": n, "detectors": k}
    q = t[t.day == MON].set_index("coil")
    y = base[MON].reindex(q.index).values
    dummies = lambda s: pd.get_dummies(s, drop_first=True).values.astype(float)
    road, prov = dummies(B.CLS.reindex(q.poly_lid).fillna("other").values), dummies(q.prov.values)
    logo = np.log10(q.obs.values)[:, None]
    res["variance_explained_monday"] = {"road_class": r2(y, road), "province": r2(y, prov), "observed_volume": r2(y, logo), "all_three": r2(y, np.column_stack([road, prov, logo]))}
    res["same_detector_across_runs"] = {}
    for name, f in ({} if adopted else RUNS).items():
        if not list(f(MON).glob(f"sim_{D.tag(MON)}_uniq_*.csv")):
            continue
        o = {}
        for d in C.CAL_DAYS:
            x = resid(t, f, d)
            o[d] = {"r_with_model": float(x.corr(base[d])), "sd_log10": float(x.std()), "median_abs_change_log10": float((x - base[d]).abs().median())}
        res["same_detector_across_runs"][name] = o
    bar = pd.read_csv(ROOT / "vars/extra/er_barriers_cartodata.csv", sep=";").drop_duplicates("tag").set_index("tag")
    c = bar.reindex(base[MON].index)
    la, lo = np.radians(c.lat.values), np.radians(c.lon.values)
    dist = 2 * 6371 * np.arcsin(np.sqrt(np.sin((la[:, None] - la) / 2) ** 2 + np.cos(la[:, None]) * np.cos(la) * np.sin((lo[:, None] - lo) / 2) ** 2))
    v = base[MON].values
    iu = np.triu_indices(len(v), 1)
    pair = lambda w, m: np.corrcoef(w[iu[0]][m], w[iu[1]][m])[0, 1]
    res["neighbours"] = {}
    for lo_, hi in BINS:
        m = (dist[iu] >= lo_) & (dist[iu] < hi)
        perm = [pair(rng.permutation(v), m) for _ in range(N_PERM)]
        res["neighbours"][f"{lo_}-{hi}km"] = {"pairs": int(m.sum()), "r": float(pair(v, m)), "null_ci95": [float(x) for x in np.percentile(perm, [2.5, 97.5])]}
    (D.RES / ("single_road_error_province.json" if adopted else "single_road_error.json")).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main("adopted" in sys.argv)
