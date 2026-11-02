#!/usr/bin/env python3
"""Final statistical tests of the frozen model on data not used to set it: test half of 2020 and all detectors of 2021.

Fixed before the outcomes below were computed (31 Oct). The volume ratio and the Spearman correlation had already been seen;
the permutation within road class, the slope, GEH and the province-cluster intervals had not. Raw simulation, no correction.

  T1 level: equivalence (two one-sided tests) of the pooled volume ratio within 0.80-1.25, 90% bootstrap interval over
     detectors and over provinces; the smallest margin that passes is reported.
  T2 ranking: Spearman above zero, permutation of the simulated volumes among detectors.
  T3 ranking beyond road class: same, permuting only within road class, so what road class alone explains is the null.
  T4 hourly shape: GPS link error of the simulation below the flat profile (Wilcoxon signed rank, one-sided), outside
     Forli-Cesena, whose traces set the route weights.
  T5 absolute standard for single roads: share of detector-hours with GEH below 5 at least 85%, the UK criterion for
     assignment models, bootstrap over detectors. No claim of accuracy at single roads holds unless the interval reaches 85%.
  Also reported, not a test of adequacy: slope of log10 simulated on log10 observed volume.
p values of T2-T4 are Holm-adjusted over the six tests. A pass supports only the property tested.

  python3 validation_tests.py -> model/results/corrected/validation_tests.json
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr, wilcoxon

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calibrate_demand as C  # noqa: E402
import demand_scaling as D  # noqa: E402
import detector_baselines as B  # noqa: E402
import direction_diagnosis as X  # noqa: E402
import od_matrix as M  # noqa: E402
import reconstruct_and_validate as P  # noqa: E402
import source_value as V  # noqa: E402
import gps_validation_split as G  # noqa: E402
from paths import ROOT  # noqa: E402
from paths import RESULTS as _RES  # noqa: E402

N_BOOT, N_PERM, SEED = 5000, 20000, 20261047
LOW, HIGH = 0.80, 1.25
PROV = pd.read_csv(ROOT / "vars/extra/er_barriers.csv", sep=";").set_index("ID").PRO
OUT = _RES / "corrected"


def geh(m, c):
    return np.sqrt(2 * (m - c) ** 2 / np.maximum(m + c, 1e-9))


def uniq(path, day):
    u = pd.read_csv(next(path.glob(f"sim_{D.tag(day)}_uniq_*.csv")), sep=";")
    return u.groupby("poly_lid")[[c for c in u if c.startswith("20")]].sum()


def table_2020():
    t = M.table("test")
    t = pd.concat([t[t.day == d] for d in C.CAL_DAYS]).reset_index(drop=True)
    obs, rows, hours = X.hourly_obs(), [], []
    for day in C.CAL_DAYS:
        u = uniq(D.OUT / "V6_scaled", day)
        for coil, lid, o in t[t.day == day][["coil", "poly_lid", "obs"]].itertuples(index=False):
            s = u.loc[lid].values.astype(float) if lid in u.index else np.zeros(24)
            rows.append(dict(coil=coil, lid=lid, obs=o, sim=s.sum()))
            hours.append(pd.DataFrame(dict(coil=coil, geh=geh(s, obs[day][f"{coil}_0"].values + obs[day][f"{coil}_1"].values))))
    r = pd.DataFrame(rows).groupby(["coil", "lid"], as_index=False).mean()
    return r, pd.concat(hours)


def table_2021():
    d = pd.read_csv(OUT / "loo_detectors.csv")
    d = d[d.day.str.startswith("2021")].dropna(subset=["raw_total"])
    r = d.groupby(["coil", "day"], as_index=False).agg(obs=("obs_total", "sum"), sim=("raw_total", "sum")).groupby("coil", as_index=False)[["obs", "sim"]].mean()
    bar = pd.read_csv(ROOT / "vars/extra/er_barriers_cartodata.csv", sep=";").set_index("tag").poly_lid
    r["lid"] = bar.reindex(r.coil).values
    obs = P.coil_table_local(2021)
    hours = []
    for day in sorted(d.day.unique()):
        z = obs[obs.index.normalize() == pd.Timestamp(day)]
        z = z.groupby(z.index.hour).sum(min_count=4)
        u = uniq(D.OUT / "V6_scaled", day)
        for coil in d[d.day == day].coil.unique():
            lid = bar[coil]
            s = u.loc[lid].values.astype(float) if lid in u.index else np.zeros(24)
            hours.append(pd.DataFrame(dict(coil=coil, geh=geh(s, (z[f"{coil}_0"] + z[f"{coil}_1"]).values))))
    return r, pd.concat(hours)


def boot_ratio(r, groups, rng, q):
    idx = {g: np.where(groups == g)[0] for g in np.unique(groups)}
    keys = list(idx)
    v = [(lambda i: r.sim.values[i].sum() / r.obs.values[i].sum())(np.concatenate([idx[k] for k in rng.choice(keys, len(keys))])) for _ in range(N_BOOT)]
    return [float(x) for x in np.percentile(v, q)]


def perm_p(x, y, strata, rng):
    obs = spearmanr(x, y)[0]
    idx = [np.where(strata == s)[0] for s in np.unique(strata)]
    hit = 0
    for _ in range(N_PERM):
        z = y.copy()
        for i in idx:
            z[i] = y[rng.permutation(i)]
        hit += spearmanr(x, z)[0] >= obs
    return float((hit + 1) / (N_PERM + 1))


def volumes(r, hours, rng):
    r = r[(r.obs > 0)].copy()
    r["prov"] = PROV.reindex(r.coil).values
    r["road"] = B.CLS.reindex(r.lid).fillna("other").values
    ratio = float(r.sim.sum() / r.obs.sum())
    ci90 = boot_ratio(r, r.coil.values, rng, [5, 95])
    ci90p = boot_ratio(r, r.prov.values, rng, [5, 95])
    x, y = r.obs.values.astype(float), r.sim.values.astype(float)
    lx, ly = np.log10(x), np.log10(np.clip(y, 1, None))
    slope = np.polyfit(lx, ly, 1)[0]
    sb = [np.polyfit(lx[i], ly[i], 1)[0] for i in (rng.integers(0, len(x), len(x)) for _ in range(N_BOOT))]
    ok = hours.dropna(subset=["geh"])
    by = ok.groupby("coil").geh.apply(lambda g: (g < 5).sum()), ok.groupby("coil").geh.size()
    keys = by[0].index.values
    g = [(lambda k: by[0][k].sum() / by[1][k].sum())(rng.choice(keys, len(keys))) for _ in range(N_BOOT)]
    margin = max(1 / min(ci90 + ci90p), max(ci90 + ci90p))
    return {"detectors": int(len(r)), "T1_level": {"ratio": ratio, "ci90_detectors": ci90, "ci90_provinces": ci90p, "equivalent_0.80_1.25": bool(min(ci90 + ci90p) > LOW and max(ci90 + ci90p) < HIGH), "smallest_symmetric_ratio_margin": float(margin)},
            "spearman": float(spearmanr(x, y)[0]), "T2_p": perm_p(x, y, np.zeros(len(x)), rng), "T3_p": perm_p(x, y, r.road.values, rng), "road_classes": r.road.value_counts().to_dict(),
            "slope_log_log": {"slope": float(slope), "ci95": [float(v) for v in np.percentile(sb, [2.5, 97.5])], "r2": float(np.corrcoef(lx, ly)[0, 1] ** 2)},
            "T5_geh": {"share_below_5": float((ok.geh < 5).mean()), "ci95": [float(v) for v in np.percentile(g, [2.5, 97.5])], "share_below_10": float((ok.geh < 10).mean()), "meets_85": bool(np.percentile(g, 97.5) >= 0.85), "hours": int(len(ok))}}


def shape(year):
    m = pd.read_csv(_RES / f"private/corrected_link_metrics_{year}_all.csv").dropna(subset=["mae_pp_raw", "mae_pp_flat"])
    m = m[~m.cid.isin(G.fc_links())]
    d = m.mae_pp_raw - m.mae_pp_flat
    return {"links": int(len(m)), "median_raw": float(m.mae_pp_raw.median()), "median_flat": float(m.mae_pp_flat.median()), "share_better": float((d < 0).mean()), "T4_p": float(wilcoxon(d, alternative="less").pvalue)}


def holm(p):
    k = sorted(p, key=p.get)
    out, top = {}, 0.0
    for i, n in enumerate(k):
        top = max(top, min(1.0, (len(k) - i) * p[n]))
        out[n] = float(top)
    return out


def main():
    rng = np.random.default_rng(SEED)
    res = {"2020_test": volumes(*table_2020(), rng), "2021": volumes(*table_2021(), rng)}
    res["2020_test"]["shape_outside_province"], res["2021"]["shape_outside_province"] = shape(2020), shape(2021)
    p = {f"{s}_{t}": (res[s][f"{t}_p"] if t != "T4" else res[s]["shape_outside_province"]["T4_p"]) for s in ("2020_test", "2021") for t in ("T2", "T3", "T4")}
    res["holm_adjusted_p"] = holm(p)
    (OUT / "validation_tests.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
