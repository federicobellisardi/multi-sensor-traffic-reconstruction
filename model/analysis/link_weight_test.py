#!/usr/bin/env python3
"""Route weights from the GPS count of each link in Forli-Cesena instead of the class. Diagnostic (results/experiments/PROTOCOL_DIAGNOSTICS.md).

  python3 link_weight_test.py jobs          simulations still to run
  python3 link_weight_test.py one NAME DAY  one simulation
  python3 link_weight_test.py evaluate      -> model/results/experiments/link_weight_test.json
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calibrate_demand as C  # noqa: E402
import demand_scaling as D  # noqa: E402
import gps_validation_split as G  # noqa: E402
import source_value as V  # noqa: E402
from paths import ROOT, RESULTS as R1  # noqa: E402

MON, SAT = C.CAL_DAYS
OUT = D.RUNS / "link_weight_test"
WEIGHTS = OUT / "link_weights_fc.cnt"
MIN_PROBES, SCALE, N_BOOT, SEED = 50, 13.5, 5000, 20261102
BASE = D.ROUTING / D.VARIANTS["V6_scaled"] / "link_weights.cnt"


def gps_daily():
    keep = set(pd.read_csv(R1 / "private/gps_links_unchanged.csv", index_col=0).query("hausdorff_m <= 1").index)
    v = pd.read_csv(ROOT / "work_viasat/viasat_20200210_20200218_timed_fluxes.csv", sep=";", parse_dates=["time"])
    v = v[v.cid.isin(keep & set(G.fc_links()))]
    days = v.time.dt.date.nunique()
    total = v.groupby("cid").total_fluxes.sum()
    return total[total >= MIN_PROBES] / days


def weights():
    g = gps_daily()
    w = pd.read_csv(BASE, sep=" ")
    new = g.reindex(w.cid)
    k = np.maximum(1, np.round(10 * new.values / SCALE))
    ch = new.notna().values
    w.loc[ch, "cntFT"] = k[ch].astype(int)
    w.loc[ch, "cntTF"] = k[ch].astype(int)
    OUT.mkdir(parents=True, exist_ok=True)
    w.to_csv(WEIGHTS, sep=" ", index=False)
    return int(ch.sum())


def jobs():
    for day in (MON, SAT):
        if not list((OUT / "fc").glob(f"sim_{D.tag(day)}_uniq_*.csv")):
            print("fc", day)


def one(name, day):
    weights()
    k = D.k_of(day)
    b = OUT / name / f"sim_{D.tag(day)}"
    c = D.v6_config(day, D.VARIANTS["V6_scaled"], D.province_scaled(D.scaled_sources(day, {x: k for x in D.CLASSES})), b)
    c["file_cnt"] = str(WEIGHTS)
    res = D.run(c, b)
    print(*res, flush=True)
    sys.exit(1 if res[1] else 0)


def stats(s, o):
    m = (s > 0)
    return spearmanr(o, s)[0], np.log10(s[m] / o[m]).std()


def paired(a, b, o, rng):
    """Differences (a - b) of Spearman and dispersion, with paired bootstrap over detectors."""
    sa, da, sb, db = *stats(a, o), *stats(b, o)
    d = []
    for _ in range(N_BOOT):
        i = rng.integers(0, len(o), len(o))
        x, y = stats(a[i], o[i]), stats(b[i], o[i])
        d.append((x[0] - y[0], x[1] - y[1]))
    q = np.nanpercentile(d, [2.5, 97.5], axis=0)
    return {"n": len(o), "spearman": [float(sa), float(sb)], "dispersion": [float(da), float(db)],
            "spearman_diff_ci95": q[:, 0].tolist(), "dispersion_diff_ci95": q[:, 1].tolist()}


def evaluate():
    rng = np.random.default_rng(SEED)
    res = {"links_changed": weights(), "weights_total_base": int(pd.read_csv(BASE, sep=" ").cntFT.sum())}
    prov = pd.read_csv(ROOT / "vars/extra/er_barriers.csv", sep=";").set_index("ID").PRO
    g = D.group_observations()
    for day, later in ((MON, "2021-06-28"), (SAT, "2021-07-03")):
        base = D.OUT / "V6_scaled"
        sets = {"2020": g[g.day == day][["coil", "poly_lid", "obs"]].reset_index(drop=True), "2021": V.later_obs(later)}
        r = {}
        for y, t in sets.items():
            inside = t.coil.map(prov).eq("FO").values
            a, b = V.daily(OUT / "fc", day, t.poly_lid), V.daily(base, day, t.poly_lid)
            o = t.obs.values
            r[y] = {"forli_cesena": paired(a[inside], b[inside], o[inside], rng), "outside": paired(a[~inside], b[~inside], o[~inside], rng)}
            if day == MON:
                s = V.daily(D.RUNS / "source_value_province/seed2", day, t.poly_lid)
                r[y]["seed2_minus_base_forli_cesena"] = paired(s[inside], b[inside], o[inside], rng)
        gd = gps_daily()
        lids = pd.read_csv(WEIGHTS, sep=" ").set_index("cid").lid.reindex(gd.index).dropna().astype(int)
        r["manipulation_spearman_gps"] = {n: float(spearmanr(V.daily(p, day, lids.values), gd.reindex(lids.index).values)[0]) for n, p in (("fc", OUT / "fc"), ("base", base))}
        res[day] = r
    (R1 / "experiments/link_weight_test.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "jobs":
        jobs()
    elif a[0] == "one":
        one(a[1], a[2])
    else:
        evaluate()
