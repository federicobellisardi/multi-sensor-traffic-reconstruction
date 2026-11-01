#!/usr/bin/env python3
"""What the OD tables add, and how much the results depend on the random seed. Frozen model otherwise.

no_od: same agents per quarter and same k, all with random origin and destination drawn from the population scores, so
the spatial structure of the OD is removed and its temporal profile is kept. Monday and Saturday.
seed: Monday repeated with seeds 2, 3, 4; regression: Monday with the default seed, must equal the frozen run.

Rule fixed before the runs (31 Oct): the OD spatial structure is supported if, on the held-out detectors of February
2020 or on the 2021 detectors, the 95% paired bootstrap interval over detectors of the Spearman difference (frozen -
no_od) lies above zero, or that of the sd of log10(sim/obs) difference lies below zero. Detectors with no simulated flow
in either run are excluded from the sd. A difference smaller than the range between seeds is not interpreted.
Daily volumes from uniq; Monday against the weekday group mean and 28 June 2021, Saturday against the weekend group mean
and 3 July 2021. Nothing in the frozen model is to be changed on this.

  python3 source_value.py jobs | one NAME DAY | evaluate -> model/results/demand/source_value.json
  python3 source_value.py gps -> model/results/demand/source_value_gps.json (rank agreement of daily link volumes with
      GPS counts, frozen against no_od, a denser test added after the detector result; probes are a sample, so no level)
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
import demand_scan_eval as E  # noqa: E402
import reconstruct_and_validate as P  # noqa: E402

OUT = D.RUNS / "source_value_province"
MON, SAT = C.CAL_DAYS
PLAN = {"no_od": [MON, SAT], "seed2": [MON], "seed3": [MON], "seed4": [MON], "regression": [MON]}
LATER = {MON: "2021-06-28", SAT: "2021-07-03"}
N_BOOT, SEED = 2000, 20261042


def base(name, day):
    return OUT / name / f"sim_{D.tag(day)}"


def jobs():
    for name, days in PLAN.items():
        for day in days:
            if not list(base(name, day).parent.glob(f"sim_{D.tag(day)}_uniq_*.csv")):
                print(name, day)


def one(name, day):
    k = D.k_of(day)
    src = D.province_scaled(D.scaled_sources(day, {x: k for x in D.CLASSES}))
    if name == "no_od":
        rate = np.sum([v["creation_rate"] for v in src.values()], axis=0)
        loc = json.loads(json.dumps(src["LOCALS"]))
        loc["creation_rate"] = [int(x) for x in rate]
        assert sum(loc["creation_rate"]) == sum(sum(v["creation_rate"]) for v in src.values())
        src = {"LOCALS": loc}
    c = D.v6_config(day, D.VARIANTS["V6_scaled"], src, base(name, day))
    if name.startswith("seed"):
        c["seed"] = int(name[4:])
    res = D.run(c, base(name, day))
    print(*res, flush=True)
    sys.exit(1 if res[1] else 0)


def daily(path, day, lids):
    d = D.link_daily(next(Path(path).glob(f"sim_{D.tag(day)}_uniq_*.csv")))
    return np.array([d.get(l, 0.0) for l in lids], dtype=float)


def later_obs(day):
    z = P.coil_table_local(2021)
    q = z[z.index.strftime("%Y-%m-%d") == day]
    bar = pd.read_csv(D.ROOT / "vars/extra/er_barriers_cartodata.csv", sep=";").drop_duplicates("tag")
    rows = [(c, l, float(q[[f"{c}_0", f"{c}_1"]].sum().sum())) for c, l in bar[["tag", "poly_lid"]].values
            if f"{c}_0" in q and f"{c}_1" in q and q[[f"{c}_0", f"{c}_1"]].notna().all().all()]
    return pd.DataFrame(rows, columns=["coil", "poly_lid", "obs"])


def sets(day):
    g = D.group_observations()
    u = g.drop_duplicates("coil").reset_index(drop=True)
    cal = set(u.coil[E.split(u)])
    h = g[(g.day == day) & ~g.coil.isin(cal)][["coil", "poly_lid", "obs"]].reset_index(drop=True)
    return {"held_out_2020": h, "all_2021": later_obs(LATER[day])}


def metrics(s, o):
    m = s > 0
    lr = np.log10(s[m] / o[m])
    return {"n": int(len(o)), "zero_flow": int((~m).sum()), "ratio": float(s.sum() / o.sum()), "spearman": float(spearmanr(o, s)[0]), "sd_log10": float(lr.std()),
            "median_abs_log10": float(np.median(np.abs(np.log10(np.clip(s, 1, None) / o)))), "within_factor2": float(np.mean(np.abs(np.log10(np.clip(s, 1, None) / o)) < np.log10(2)))}


def evaluate():
    done = [(n, d) for n, ds in PLAN.items() for d in ds if list(base(n, d).parent.glob(f"sim_{D.tag(d)}_uniq_*.csv"))]
    assert len(done) == sum(map(len, PLAN.values())), done
    rng = np.random.default_rng(SEED)
    out = {"rule": __doc__.split("Rule fixed")[1].split("Daily volumes")[0].strip(), "comparison": {}}
    for day in (MON, SAT):
        ref = D.OUT / "V6_scaled"
        out["comparison"][day] = {}
        for name, t in sets(day).items():
            o = t.obs.values
            a, b = daily(ref, day, t.poly_lid), daily(base("no_od", day).parent, day, t.poly_lid)
            n = len(o)
            sd = lambda s, i: np.log10(s[i] / o[i]).std()
            keep = np.where((a > 0) & (b > 0))[0]
            ds = [spearmanr(o[i], a[i])[0] - spearmanr(o[i], b[i])[0] for i in (rng.integers(0, n, n) for _ in range(N_BOOT))]
            dv = [sd(a, i) - sd(b, i) for i in (rng.choice(keep, len(keep)) for _ in range(N_BOOT))]
            med = [np.median(np.abs(np.log10(np.clip(a[i], 1, None) / o[i]))) - np.median(np.abs(np.log10(np.clip(b[i], 1, None) / o[i]))) for i in (rng.integers(0, n, n) for _ in range(N_BOOT))]
            ci = lambda v: [float(x) for x in np.percentile(v, [2.5, 97.5])]
            out["comparison"][day][name] = {"frozen": metrics(a, o), "no_od": metrics(b, o), "spearman_diff": float(spearmanr(o, a)[0] - spearmanr(o, b)[0]), "spearman_diff_ci95": ci(ds),
                                            "sd_diff": float(sd(a, keep) - sd(b, keep)), "sd_diff_ci95": ci(dv), "median_abs_log10_diff_ci95": ci(med),
                                            "supported": bool(ci(ds)[0] > 0 or ci(dv)[1] < 0)}
    ref = D.OUT / "V6_scaled"
    a, b = next(ref.glob(f"sim_{D.tag(MON)}_uniq_*.csv")), next(base("regression", MON).parent.glob(f"sim_{D.tag(MON)}_uniq_*.csv"))
    out["regression_identical"] = a.read_bytes() == b.read_bytes()
    t = sets(MON)["held_out_2020"]
    o = t.obs.values
    runs = {"seed1": daily(ref, MON, t.poly_lid)} | {s: daily(base(s, MON).parent, MON, t.poly_lid) for s in ("seed2", "seed3", "seed4")}
    M = np.array(list(runs.values()))
    pos = (M > 0).all(axis=0)
    cv = M[:, pos].std(axis=0, ddof=1) / M[:, pos].mean(axis=0)
    out["seeds"] = {"by_seed": {k: metrics(v, o) for k, v in runs.items()}, "coil_cv_quartiles": [float(x) for x in np.percentile(cv, [25, 50, 75])], "coil_cv_max": float(cv.max()),
                    "range": {m: float(max(metrics(v, o)[m] for v in runs.values()) - min(metrics(v, o)[m] for v in runs.values())) for m in ("ratio", "spearman", "sd_log10", "median_abs_log10")}}
    (D.RES / "source_value.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


def gps():
    import gps_validation_split as G
    fc = G.fc_links()
    keep = P.unchanged_gps_links()
    rng = np.random.default_rng(SEED + 1)
    out = {}
    for year, gname in P.CAMPAIGNS.items():
        v = pd.read_csv(D.ROOT / "work_viasat" / gname, sep=";", parse_dates=["time"])
        v = v[v.cid.isin(keep)]
        for day in (MON, SAT):
            obs_day = day if year == 2020 else LATER[day]
            g = v[v.time.dt.strftime("%Y-%m-%d") == obs_day].groupby("cid").total_fluxes.sum()
            g = g[g > 0]
            f = lambda path: (lambda d: d.groupby("poly_cid")[[c for c in d if c.startswith("20")]].sum().sum(axis=1))(pd.read_csv(next(Path(path).glob(f"sim_{D.tag(day)}_uniq_*.csv")), sep=";")).reindex(g.index).fillna(0).values
            a, b = f(D.OUT / "V6_scaled"), f(base("no_od", day).parent)
            ins = g.index.isin(fc)
            for where, m in (("forli_cesena", ins), ("rest_of_region", ~ins)):
                o, x, y = g.values[m], a[m], b[m]
                n = len(o)
                d = [spearmanr(o[i], x[i])[0] - spearmanr(o[i], y[i])[0] for i in (rng.integers(0, n, n) for _ in range(N_BOOT))]
                out[f"{year}_{'weekday' if day == MON else 'weekend'}_{where}"] = {"links": n, "spearman_frozen": float(spearmanr(o, x)[0]), "spearman_no_od": float(spearmanr(o, y)[0]), "diff_ci95": [float(q) for q in np.percentile(d, [2.5, 97.5])]}
    (D.RES / "source_value_gps.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out))


if __name__ == "__main__":
    {"jobs": jobs, "evaluate": evaluate, "gps": gps}.get(sys.argv[1], lambda: one(*sys.argv[2:]))()
