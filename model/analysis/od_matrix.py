#!/usr/bin/env python3
"""Demand with the N most active municipalities of Emilia-Romagna as origins and destinations.

Selection from the OD tables: inter-municipal trips in plus out over all days of the week of the clean period. Relations
between selected municipalities keep both endpoints; one selected end gives src_rnd or rnd_dest, none gives rnd_rnd, as in
the existing generator (province relations unchanged). Unlike it, hourly means are not truncated and quarters use
cumulative rounding, so small relations are not lost. r: radius (km) of the endpoint spread of the relations; random
classes stay at the frozen 20 km. k is the frozen one: agents fall as N grows, so the level is tuned only if a
configuration is adopted.

Rule fixed before the runs (31 Oct): on the calibration half, group means of Monday and Saturday together, a configuration
beats the frozen model if the 95% paired bootstrap interval over detectors of the sd of log10(sim/obs) difference lies below
zero, or that of the Spearman difference lies above zero with the sd not worse (interval upper end not above zero is not
required, its point estimate must not be higher). Among those, the lowest sd is selected. It is adopted only if confirmed
in the same direction on the 2021 detectors, with interval excluding zero on the same metric; the held-out half of
2020 is reported, already seen. Differences within the seed range (Spearman 0.009) are not interpreted.

Amendment before any result was read (31 Oct, user: destination code 000000000 is an error in the file): names ending in _x
drop those cells and multiply k so that the total of agents is unchanged. They are the primary grid and the selection is
made among them; the grid without _x is kept as a sensitivity check.

  python3 od_matrix.py jobs | one NAME DAY | check | evaluate -> model/results/demand/od_matrix.json
"""
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_od_configs as B  # noqa: E402
import calibrate_demand as C  # noqa: E402
import demand_scaling as D  # noqa: E402
import demand_scan_eval as E  # noqa: E402
import source_value as V  # noqa: E402
from paths import ROOT  # noqa: E402
from paths import RESULTS as _RES  # noqa: E402

OUT = D.RUNS / "od_matrix"
FROZEN = D.RUNS / f"radius_scan/r{int(D.CHERRY_RADIUS_KM)}"
NS, RADII = (50, 100, 200, 347), (5, 20)
PRIMARY = [f"N{n}_r{r}_x" for n in NS for r in RADII]
GRID = [f"N{n}_r{r}" for n in NS for r in RADII] + PRIMARY
MIN_NODES = 3
N_BOOT, SEED = 2000, 20261044
COM = pd.read_csv(ROOT / "vars/extra/italy_com.csv", sep=";", dtype={"UID": str}).set_index("UID")


def base(name, day):
    return OUT / name / f"sim_{D.tag(day)}"


def parse(name):
    n, r = name.split("_")[:2]
    return int(n[1:]), int(r[1:])


def cache():
    return pickle.load(open(D.RUNS / "od_cells_cache.pkl", "rb"))


def ranking(sums):
    x = pd.concat(list(sums["clean"].values())).groupby(level=[0, 1]).sum()
    x = x[x.index.get_level_values(0) != x.index.get_level_values(1)]
    io = x.groupby(level=0).sum().add(x.groupby(level=1).sum(), fill_value=0)
    return io[io.index.isin(COM.index[COM.REG == 8])].sort_values(ascending=False)


def quarters(hourly, k):
    """Cumulative rounding: the daily total is preserved and small hourly values are not lost."""
    q = np.repeat(np.asarray(hourly, float) * k / 4, 4)
    c = np.round(np.cumsum(q))
    return [int(v) for v in np.diff(np.concatenate([[0], c]))]


def nodes():
    g = json.load(open(_RES / "carto_a059fb0.geojson"))["features"]
    p = {tuple(f["geometry"]["coordinates"][i]) for f in g for i in (0, -1)}
    return np.radians(np.array(sorted(p))[:, ::-1])


def near(lat, lon, xy, km):
    a, b = np.radians(lat), np.radians(lon)
    d = 2 * 6371 * np.arcsin(np.sqrt(np.sin((xy[:, 0] - a) / 2) ** 2 + np.cos(a) * np.cos(xy[:, 0]) * np.sin((xy[:, 1] - b) / 2) ** 2))
    return int((d <= km).sum())


def sources(name, day, m=1.0):
    n, r = parse(name)
    sums, cnt, _ = cache()
    wd, k = pd.Timestamp(day).weekday(), D.k_of(day)
    top = list(ranking(sums).index[:n])
    act = set(top)
    tpl = json.load(open(D.CONF / f"{day}.json"))["sources"]
    pawn = {}
    for v in tpl.values():
        pawn.setdefault(next(iter(v["pawns"])), v)
    src = {a: b for a, b in D.scaled_sources(day, {x: k for x in D.CLASSES}).items() if "scr_dest_prov" in b["pawns"]}
    rel, org, dst, loc = {}, {}, {}, np.zeros(24)
    drop, dropped = name.endswith("_x"), 0.0
    code = B.province_codes()
    relations = {tuple(code[x] for x in a[:-3].split("_")) for a in src} if B.NO_PROVINCE_COPY else set()
    for h in range(24):
        s = sums["clean"][wd, h] / cnt["clean"][wd]
        for (o, d), v in s.items():
            if drop and d == B.FOREIGN:
                dropped += v
                continue
            oa, da = o in act, d in act
            if oa and da:
                if o != d:
                    rel.setdefault((o, d), np.zeros(24))[h] += v
            elif (o[:6], d[:6]) in relations:
                continue
            elif oa:
                org.setdefault(o, np.zeros(24))[h] += v
            elif da:
                dst.setdefault(d, np.zeros(24))[h] += v
            else:
                loc[h] += v
    kept = sum(v.sum() for v in rel.values()) + sum(v.sum() for v in org.values()) + sum(v.sum() for v in dst.values()) + loc.sum()
    f = m * (kept + dropped) / kept if not D.NO_CODE else m  # without the code in the model, k is already set on the demand without it
    k *= f
    for b in src.values():
        b["creation_rate"] = [int(round(f * v)) for v in b["creation_rate"]]
    xy = nodes() if r < 20 else None
    where = lambda i: {"lat": float(COM.LAT[i]), "lon": float(COM.LON[i])}
    def add(key, kind, rate, **place):
        q = quarters(rate, k)
        if sum(q):
            c = json.loads(json.dumps(pawn[kind]))
            for f in ("source_location", "dest_location"):
                c.pop(f, None)
            c.update(place, creation_rate=q)
            src[key] = c
    sparse = 0
    for (o, d), v in rel.items():
        add(f"{o}_{d}_IN", "scr_dest", v, source_location=where(o), dest_location=where(d))
        if r < 20 and f"{o}_{d}_IN" in src:
            if min(near(COM.LAT[o], COM.LON[o], xy, r), near(COM.LAT[d], COM.LON[d], xy, r)) >= MIN_NODES:
                src[f"{o}_{d}_IN"]["pawns"]["scr_dest"]["cherry_pick"] = "small"
            else:
                sparse += 1
    for o, v in org.items():
        add(f"{o}_src_IN", "src_rnd", v, source_location=where(o))
    for d, v in dst.items():
        add(f"{d}_dest_OUT", "rnd_dest", v, dest_location=where(d))
    add("LOCALS", "rnd_rnd", loc)
    return src, sparse


def config(name, day, m=1.0, path=None):
    _, r = parse(name)
    src, sparse = sources(name, day, m)
    c = D.v6_config(day, D.VARIANTS["V6_scaled"], src, path or base(name, day))
    if r < 20:
        c["cherry_pick_mode"]["small"] = float(r)
    return c, sparse


def jobs():
    for name in GRID:
        for day in C.CAL_DAYS:
            if not list(base(name, day).parent.glob(f"sim_{D.tag(day)}_uniq_*.csv")):
                print(name, day)


def one(name, day):
    c, _ = config(name, day)
    res = D.run(c, base(name, day))
    print(*res, flush=True)
    sys.exit(1 if res[1] else 0)


def check():
    sums, _, names = cache()
    print([names[i] for i in ranking(sums).index[:5]])
    frozen = json.load(open(FROZEN / f"k{D.k_of(C.CAL_DAYS[0]):.1f}" / f"sim_{D.tag(C.CAL_DAYS[0])}.json"))["sources"]
    print("Bologna frozen", frozen["Bologna_src_IN"]["source_location"], "new", COM.loc[COM.COM_NAME == "Bologna"][["LAT", "LON"]].values.tolist())
    for name in ("N50_r20_x", "N347_r5_x"):
        for day in C.CAL_DAYS:
            c, sparse = config(name, day)
            t = {}
            for v in c["sources"].values():
                kk = next(iter(v["pawns"]))
                t.setdefault(kk, [0, 0])
                t[kk][0] += 1
                t[kk][1] += sum(v["creation_rate"])
            print(name, day, "sources", len(c["sources"]), t, "sparse", sparse, {x: (f(next(iter(c["sources"].values()))["creation_rate"])) for x, f in {"len": len}.items()})
    print("frozen", sum(sum(v["creation_rate"]) for v in frozen.values()))


def table(split):
    g = D.group_observations()
    u = g.drop_duplicates("coil").reset_index(drop=True)
    cal = set(u.coil[E.split(u)])
    return g[g.coil.isin(cal) if split == "cal" else ~g.coil.isin(cal)].reset_index(drop=True)


def daily(path_of, t):
    return np.concatenate([V.daily(path_of(day), day, t[t.day == day].poly_lid) for day in C.CAL_DAYS])


def compare(t, a, b, rng):
    t = pd.concat([t[t.day == day] for day in C.CAL_DAYS]).reset_index(drop=True)
    o, coil = t.obs.values, t.coil.values
    us = np.unique(coil)
    idx = {c: np.where(coil == c)[0] for c in us}
    sd = lambda s, i: np.log10(np.clip(s[i], 1, None) / o[i]).std()
    sp = lambda s, i: spearmanr(o[i], s[i])[0]
    res = lambda s: {"ratio": float(s.sum() / o.sum()), "sd_log10": float(sd(s, np.arange(len(o)))), "spearman": float(sp(s, np.arange(len(o)))), "median_abs_log10": float(np.median(np.abs(np.log10(np.clip(s, 1, None) / o))))}
    ds, dp = [], []
    for _ in range(N_BOOT):
        i = np.concatenate([idx[c] for c in rng.choice(us, len(us))])
        ds.append(sd(a, i) - sd(b, i))
        dp.append(sp(a, i) - sp(b, i))
    return {"rows": int(len(o)), "new": res(a), "frozen": res(b), "sd_diff_ci95": [float(x) for x in np.percentile(ds, [2.5, 97.5])], "spearman_diff_ci95": [float(x) for x in np.percentile(dp, [2.5, 97.5])]}


def frozen_path(day):
    return FROZEN / f"k{D.k_of(day):.1f}"


def evaluate():
    t = table("cal")
    b = daily(frozen_path, t)
    rng = np.random.default_rng(SEED)
    out = {}
    for name in GRID:
        a = daily(lambda d: base(name, d).parent, t)
        out[name] = compare(t, a, b, rng)
        c = out[name]
        c["beats_frozen"] = bool(c["sd_diff_ci95"][1] < 0 or (c["spearman_diff_ci95"][0] > 0 and c["new"]["sd_log10"] <= c["frozen"]["sd_log10"]))
    ok = [n for n in PRIMARY if out[n]["beats_frozen"]]
    res = {"calibration": out, "selected": min(ok, key=lambda n: out[n]["new"]["sd_log10"]) if ok else None}
    (D.RES / "od_matrix.json").write_text(json.dumps(res, indent=1) + "\n")
    for n in GRID:
        c = out[n]
        print(n, round(c["new"]["ratio"], 3), round(c["new"]["sd_log10"], 4), round(c["new"]["spearman"], 3), round(c["new"]["median_abs_log10"], 3), [round(x, 4) for x in c["sd_diff_ci95"]], [round(x, 3) for x in c["spearman_diff_ci95"]], c["beats_frozen"])
    print("frozen", {k: round(v, 3) for k, v in out[GRID[0]]["frozen"].items()}, "selected", res["selected"])


if __name__ == "__main__":
    {"jobs": jobs, "check": check, "evaluate": evaluate}.get(sys.argv[1], lambda: one(*sys.argv[2:]))()
