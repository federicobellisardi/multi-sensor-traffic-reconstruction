#!/usr/bin/env python3
"""Simulations of the experiments on the frozen model (model/results/experiments/PROTOCOL.md). Changes nothing in the frozen model.

  python3 final_experiments.py jobs              simulations that can run now (second rounds wait for their first rounds)
  python3 final_experiments.py one NAME DAY      one simulation
Outputs: $SIM_RUNS/final_experiments/<name>/. Evaluation: final_experiments_eval.py.
"""
import json
import os
import pickle
import sys
from datetime import date
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_od_configs as B  # noqa: E402
import calibrate_demand as C  # noqa: E402
import demand_scaling as D  # noqa: E402
import gps_validation_split as G  # noqa: E402
import od_matrix as M  # noqa: E402
import province_demand as PD  # noqa: E402
import source_value as V  # noqa: E402
from paths import ROOT, RESULTS as R1  # noqa: E402

OUT = D.RUNS / "final_experiments"
MON, SAT = C.CAL_DAYS
DAYS = [MON, SAT]
LD = (date(2020, 3, 16), date(2020, 3, 28))
GPS, DEFAULT = D.ROUTING / "V6_gps_usage_classweights/carto", D.ROUTING / "V0_default_distance/carto"
W1 = D.ROUTING / "V6_gps_usage_classweights/link_weights.cnt"
ROUTES = {"r_V0": (DEFAULT, 1.0, 0.0, None), "r_V1": (GPS, 1.0, 0.0, None), "r_V2": (GPS, 0.0, 1.0, None), "r_V3": (GPS, 0.5, 0.5, None),
          "r_V4": (GPS, 0.0, 1.0, W1), "r_V5": (GPS, 0.0, 1.0, OUT / "weights_sqrt.cnt"), "r_D1": (DEFAULT, 0.5, float(os.environ.get("ALPHA_S", 0.0)), W1)}
if not D.NO_CODE:
    ROUTES["r_T1"] = (GPS, 0.5, 0.0, OUT / "weights_rest.cnt")
ALPHA = {"a_w100_s000": (1.0, 0.0), "a_w075_s025": (0.75, 0.25), "a_w050_s050": (0.5, 0.5), "a_w025_s075": (0.25, 0.75), "a_w000_s100": (0.0, 1.0), "a_w025_s025": (0.25, 0.25), "a_w050_s025": (0.5, 0.25)}
if os.environ.get("ALPHA_S"):
    del ALPHA["a_w050_s025"]
    ALPHA["a_w050_s000"] = (0.5, 0.0)
KS = {d: [round(D.k_of(d) + x, 1) for x in (-0.3, -0.2, -0.1, 0.1, 0.2)] for d in DAYS} if D.NO_CODE else {MON: [0.7, 0.8, 0.9, 1.1, 1.2], SAT: [0.7, 0.9, 1.0, 1.1, 1.2]}
MULT = [1.0, 1.15, 1.3]
SUB = [(n, r) for n in (25, 50) for r in range(3)]
SEED_SUB = 20261050


def base(name, day):
    return OUT / name / f"sim_{D.tag(day)}"


def no_relations_no_factors():
    """Simulation without relations and without province factors."""
    return OUT / "nofact_no_od" if D.NO_CODE else D.RUNS / "source_value/no_od"


def done(name, day):
    return bool(list(base(name, day).parent.glob(f"sim_{D.tag(day)}_uniq_*.csv")))


def names():
    out = [("regression", MON), ("regression_cluster", MON), ("fact_no_od", MON), ("fact_no_od", SAT)]
    out += [("nofact_no_od", d) for d in DAYS] if D.NO_CODE else [(f"{n}", d) for n in ("ld", "ld_no_od") for d in DAYS]
    out += [(n, d) for n in list(ROUTES) + list(ALPHA) for d in DAYS]
    out += [(f"k_{x}", d) for d in DAYS for x in KS[d]]
    out += [(f"ext_m{m}", d) for m in MULT for d in DAYS]
    out += [(f"seed{s}", SAT) for s in (2, 3, 4)]
    out += [(f"sub{n}_{r}_r1", d) for n, r in SUB for d in DAYS]
    out += [(f"sub{n}_{r}_r2", d) for n, r in SUB for d in DAYS]
    return out


def jobs():
    for n, d in names():
        if done(n, d):
            continue
        if n.endswith("_r2") and not all(done(n[:-1] + "1", x) for x in DAYS):
            continue
        print(n, d)


def model_sources(day, k=None):
    k = D.k_of(day) if k is None else k
    return D.province_scaled(D.scaled_sources(day, {x: k for x in D.CLASSES}))


def weights(path, table):
    rcl = pd.read_csv(R1 / "road_class.csv").set_index("poly_cid").road_class
    pro = pd.read_csv(ROOT / "vars/carto/er-speed.pro", sep=r"\s+", header=None, skiprows=1, usecols=[0], names=["cid"])
    rows = ["lid cid cntFT cntTF"]
    for lid, cid in enumerate(pro.cid):
        k = max(1, int(round(10 * table.get(rcl.get(cid, "unclassified"), 1.0))))
        rows.append(f"{lid} {cid} {k} {k}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(rows) + "\n")


def rest_weights():
    keep = set(pd.read_csv(R1 / "private/gps_links_unchanged.csv", index_col=0).query("hausdorff_m <= 1").index)
    v = pd.read_csv(ROOT / "work_viasat/viasat_20200210_20200218_timed_fluxes.csv", sep=";", parse_dates=["time"])
    v = v[v.cid.isin(keep)]
    g = v.groupby("cid").total_fluxes.sum() / v.time.dt.date.nunique()
    g = g[(g > 0) & ~g.index.isin(G.fc_links())]
    rc = pd.read_csv(R1 / "road_class.csv").set_index("poly_cid").road_class
    t = g.groupby(rc.reindex(g.index)).agg(["size", "median"])
    t.columns = ["links", "median_daily_gps"]
    t.to_csv(R1 / "experiments/class_gps_weights_rest.csv")
    b = t.median_daily_gps.drop("unmatched", errors="ignore")
    return b / b.min()


def ensure_weights():
    if not (OUT / "weights_sqrt.cnt").exists():
        b = pd.read_csv(R1 / "routing/class_gps_weights.csv", index_col=0).median_daily_gps.drop("unmatched", errors="ignore")
        weights(OUT / "weights_sqrt.cnt", (b / b.min()) ** 0.5)
    if not D.NO_CODE and not (OUT / "weights_rest.cnt").exists():
        weights(OUT / "weights_rest.cnt", rest_weights())


def route(c, carto, a_we, a_s, cnt):
    c["file_pro"], c["file_pnt"] = str(carto / "er-speed.pro"), str(carto / "er-speed.pnt")
    for s in c["sources"].values():
        for p in s.get("pawns", {}).values():
            p["alpha_we"], p["alpha_speed"] = a_we, a_s
    c.pop("file_cnt", None)
    if cnt:
        c["file_cnt"] = str(cnt)
    return c


def cfg(src, name, day):
    return D.v6_config(day, D.VARIANTS["V6_scaled"], src, base(name, day))


def locals_only(src):
    rate = np.sum([v["creation_rate"] for v in src.values()], axis=0)
    loc = json.loads(json.dumps(src["LOCALS"]))
    loc["creation_rate"] = [int(x) for x in rate]
    assert sum(loc["creation_rate"]) == sum(sum(v["creation_rate"]) for v in src.values())
    return {"LOCALS": loc}


def score_with_pattern():
    f = OUT / "score_pattern.csv"
    if f.exists():
        return f
    factors = json.load(open(D.RES / "province_factors.json"))
    s = pd.read_csv(ROOT / "vars/extra/node_score_pop2021.csv", sep=";")
    g = gpd.read_file(ROOT / "er-carto.geojson")
    rows = [(n, c[0], c[1]) for n, f in zip(g.poly_nF, g.geometry) for c in [f.coords[0]]] + [(n, c[0], c[1]) for n, f in zip(g.poly_nT, g.geometry) for c in [f.coords[-1]]]
    p = pd.DataFrame(rows, columns=["cid", "lon", "lat"]).drop_duplicates("cid")
    p = gpd.GeoDataFrame(p, geometry=gpd.points_from_xy(p.lon, p.lat), crs=4326)
    prov = gpd.sjoin(p, PD.SHAPES.to_crs(4326)[["PRO_NAME", "geometry"]], how="left", predicate="within").drop_duplicates("cid").set_index("cid").PRO_NAME
    code = prov.map(PD.X.CODE)
    assert code.notna().mean() > 0.9, code.notna().mean()
    m = code.reindex(s.node_cid).map(factors).fillna(1.0).pow(0.5).values
    s["score"] = s.score.values * m
    f.parent.mkdir(parents=True, exist_ok=True)
    s.to_csv(f, sep=";", index=False)
    return f


def lockdown_sources(day):
    f = OUT / "od_lockdown.pkl"
    if f.exists():
        sums, n, names_ = pickle.load(open(f, "rb"))
    else:
        sums, n, names_ = B.accumulate({"ld": LD})
        f.parent.mkdir(parents=True, exist_ok=True)
        pickle.dump((sums, n, names_), open(f, "wb"))
    tpl = json.load(open(D.CONF / f"{day}.json"))
    wd = pd.Timestamp(day).weekday()
    rates = B.build(tpl, {h: sums["ld"][wd, h] for h in range(24)}, n["ld"][wd], names_)
    k = D.k_of(day)
    src = tpl["sources"]
    for name, s in src.items():
        s["creation_rate"] = [int(round(k * v)) for v in rates[name]]
    return D.province_scaled(src)


def subset(n, rep):
    t = M.table("cal")
    u = t.drop_duplicates("coil")
    rng = np.random.default_rng(SEED_SUB + 100 * n + rep)
    shares = u.groupby("prov").coil.apply(list)
    take = {p: max(1, int(round(n * len(c) / len(u)))) for p, c in shares.items()}
    return sorted(c for p, cs in shares.items() for c in rng.permutation(cs)[:take[p]])


def sub_factors(n, rep, rnd):
    f = OUT / f"sub{n}_{rep}_factors_r{rnd}.json"
    if f.exists():
        return json.load(open(f))
    prev = sub_factors(n, rep, rnd - 1) if rnd > 1 else {p: 1.0 for p in PD.X.CODE.values()}
    path = (lambda d: M.frozen_path(d)) if rnd == 1 else (lambda d: OUT / f"sub{n}_{rep}_r{rnd - 1}")
    t = M.table("cal")
    t = t[t.coil.isin(subset(n, rep))]
    r = pd.concat(pd.Series(np.log10(np.clip(V.daily(path(d), d, q.poly_lid), 1, None) / q.obs.values), index=q.coil.values) for d, q in t.groupby("day"))
    med = r.groupby(PD.PROV.reindex(r.index).values).median()
    new = {p: float(np.clip(prev[p] * 10 ** (-med.get(p, 0.0)), 0.5, 2.5)) for p in prev}
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(new, indent=1) + "\n")
    return new


def config(name, day):
    if name.startswith("regression"):
        return cfg(model_sources(day), name, day)
    if name == "fact_no_od":
        c = cfg(locals_only(model_sources(day)), name, day)
        c["file_score_pop"] = str(score_with_pattern())
        return c
    if name == "nofact_no_od":
        k = D.k_of(day)
        return cfg(locals_only(D.scaled_sources(day, {x: k for x in D.CLASSES})), name, day)
    if name == "ld":
        return cfg(lockdown_sources(day), name, day)
    if name == "ld_no_od":
        return cfg(locals_only(lockdown_sources(day)), name, day)
    if name in ROUTES:
        ensure_weights()
        return route(cfg(model_sources(day), name, day), *ROUTES[name])
    if name in ALPHA:
        return route(cfg(model_sources(day), name, day), GPS, *ALPHA[name], W1)
    if name.startswith("k_"):
        return cfg(model_sources(day, float(name[2:])), name, day)
    if name.startswith("ext_m"):
        c, _ = M.config("N100_r20_x", day, float(name[5:]), base(name, day))
        c["sources"] = D.province_scaled(c["sources"])
        return c
    if name.startswith("seed"):
        c = cfg(model_sources(day), name, day)
        c["seed"] = int(name[4:])
        return c
    if name.startswith("sub"):
        n, rep, rnd = name[3:].split("_")
        f = sub_factors(int(n), int(rep), int(rnd[1:]))
        k = D.k_of(day)
        src = D.scaled_sources(day, {x: k for x in D.CLASSES})
        for s in src.values():
            ends = [f[p] for p in (PD.prov_of(s[e]) for e in ("source_location", "dest_location") if e in s) if p]
            if ends:
                g = float(np.prod(ends)) ** (1 / len(ends))
                s["creation_rate"] = [int(round(g * v)) for v in s["creation_rate"]]
        return cfg(src, name, day)
    raise ValueError(name)


def one(name, day):
    res = D.run(config(name, day), base(name, day))
    print(*res, flush=True)
    sys.exit(1 if res[1] else 0)


if __name__ == "__main__":
    if sys.argv[1] == "jobs":
        jobs()
    else:
        one(sys.argv[2], sys.argv[3])
