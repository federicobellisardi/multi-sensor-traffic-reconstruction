#!/usr/bin/env python3
"""Demand factor by province, set on the calibration half, tested on the test half and on 2021.

Rule fixed before the runs (31 Oct). Each located source is multiplied by the geometric mean of the factors of its ends inside
the region; ends outside and unlocated random sources (LOCALS) keep 1. Factors: start from 1, multiply by 10^(-median log10
ratio) of the calibration detectors of the province (both day types), two rounds, clipped to 0.5-2.5. k stays frozen.
A gain requires, on the test half (group means, both day types), a 95% paired bootstrap interval of the dispersion difference
below zero. If so, and only then, the 2021 detectors are read: adopted if the same interval lies below zero there. The test
half has been seen for the frozen model, 2021 is the confirmation. Nine parameters are added, so the gain must also exceed
the variability between seeds (Spearman 0.009).

  python3 province_demand.py factors ROUND | one ROUND DAY | evaluate | confirm -> model/results/demand/province_demand.json
"""
import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calibrate_demand as C  # noqa: E402
import demand_scaling as D  # noqa: E402
import detector_placement as X  # noqa: E402
import od_matrix as M  # noqa: E402
import source_value as V  # noqa: E402
from paths import ROOT  # noqa: E402

OUT = D.RUNS / "province_demand"
PROV = pd.read_csv(ROOT / "vars/extra/er_barriers.csv", sep=";").set_index("ID").PRO
SHAPES = gpd.read_file(ROOT / "vars/extra/er-shapes.geojson").to_crs(4326)
N_BOOT, SEED = 2000, 20261049


def path(rnd, day=None):
    return OUT / f"round{rnd}"


def factors_file(rnd):
    return OUT / f"factors_round{rnd}.json"


def prov_of(loc):
    p = gpd.points_from_xy([loc["lon"]], [loc["lat"]])[0]
    h = SHAPES[SHAPES.contains(p)]
    return X.CODE.get(h.PRO_NAME.iloc[0]) if len(h) else None


def residuals(t, rnd):
    f = (lambda d: M.frozen_path(d)) if rnd == 0 else (lambda d: path(rnd))
    out = []
    for d in C.CAL_DAYS:
        q = t[t.day == d]
        out.append(pd.Series(np.log10(np.clip(V.daily(f(d), d, q.poly_lid), 1, None) / q.obs.values), index=q.coil.values))
    return pd.concat(out)


def factors(rnd):
    """Factors for round rnd, from the residuals of round rnd-1."""
    t = M.table("cal")
    r = residuals(t, rnd - 1)
    prev = json.load(open(factors_file(rnd - 1))) if rnd > 1 else {p: 1.0 for p in X.CODE.values()}
    med = r.groupby(PROV.reindex(r.index).values).median()
    new = {p: float(np.clip(prev[p] * 10 ** (-med.get(p, 0.0)), 0.5, 2.5)) for p in prev}
    OUT.mkdir(parents=True, exist_ok=True)
    factors_file(rnd).write_text(json.dumps(new, indent=1) + "\n")
    print(new)


def one(rnd, day):
    rnd = int(rnd)
    f = json.load(open(factors_file(rnd)))
    k = D.k_of(day)
    src = D.scaled_sources(day, {x: k for x in D.CLASSES})
    for s in src.values():
        ends = [prov_of(s[e]) for e in ("source_location", "dest_location") if e in s]
        ends = [f[p] for p in ends if p]
        if ends:
            g = float(np.prod(ends)) ** (1 / len(ends))
            s["creation_rate"] = [int(round(g * v)) for v in s["creation_rate"]]
    b = path(rnd) / f"sim_{D.tag(day)}"
    b.parent.mkdir(parents=True, exist_ok=True)
    res = D.run(D.v6_config(day, D.VARIANTS["V6_scaled"], src, b), b)
    print(*res, flush=True)
    sys.exit(1 if res[1] else 0)


def evaluate():
    rng = np.random.default_rng(SEED)
    res = {"factors": {r: json.load(open(factors_file(r))) for r in (1, 2) if factors_file(r).exists()}}
    for half in ("cal", "test"):
        t = M.table(half)
        b = M.daily(M.frozen_path, t)
        res[half] = {f"round{r}": M.compare(t, M.daily(lambda d: path(r), t), b, rng) for r in res["factors"]}
    r = max(res["factors"])
    res["gain_on_test"] = bool(res["test"][f"round{r}"]["sd_diff_ci95"][1] < 0)
    (D.RES / "province_demand.json").write_text(json.dumps(res, indent=1) + "\n")
    for half in ("cal", "test"):
        for k, c in res[half].items():
            print(half, k, {a: round(v, 3) for a, v in c["new"].items()}, "frozen", {a: round(v, 3) for a, v in c["frozen"].items()}, "sd", [round(x, 4) for x in c["sd_diff_ci95"]], "sp", [round(x, 3) for x in c["spearman_diff_ci95"]])
    print("gain on test", res["gain_on_test"], res["factors"])


def confirm():
    """2021, round 2 against the frozen runs: per detector, mean over complete days, both directions."""
    rng = np.random.default_rng(SEED + 1)
    o = D.observations()
    o = o[o.year == 2021].reset_index(drop=True)
    a = pd.concat([pd.Series(V.daily(path(2), d, q.poly_lid), index=q.index) for d, q in o.groupby("day")]).reindex(o.index).values
    b = pd.concat([pd.Series(V.daily(D.RUNS / "demand_before_province/V6_scaled", d, q.poly_lid), index=q.index) for d, q in o.groupby("day")]).reindex(o.index).values
    g = o.assign(a=a, b=b).groupby("coil")[["obs", "a", "b"]].mean()
    t = pd.DataFrame(dict(coil=g.index, day=C.CAL_DAYS[0], obs=g.obs.values))
    c = M.compare(t, g.a.values, g.b.values, rng)
    c["adopted"] = bool(c["sd_diff_ci95"][1] < 0)
    res = json.load(open(D.RES / "province_demand.json"))
    res["confirmation_2021"] = c
    (D.RES / "province_demand.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(c, indent=1))


if __name__ == "__main__":
    {"factors": lambda: factors(int(sys.argv[2])), "evaluate": evaluate, "confirm": confirm}.get(sys.argv[1], lambda: one(*sys.argv[2:]))()
