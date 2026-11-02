#!/usr/bin/env python3
"""OD configurations from the raw TIM tables, with a chosen period for the mean by weekday.

The generator of work/conf_noaug is not available; its logic is python/od/od-model.py (mean by weekday and hour,
truncated to integer per cell) and python/webservice/conf.py (classes of sources, rate = round(hourly value / 4),
a zero rate takes the previous value), with OD hour h injected in [h, h+1). Here the existing configurations
are the template: only creation_rate changes, so sources, locations and parameters stay the same.
Acceptance test: with the period of the existing configurations (January-February 2020) the rates must be
reproduced. The clean period is 13 January - 23 February 2020 (no holidays around 6 January, no Covid days).

  python3 build_od_configs.py         acceptance test and comparison -> model/results/demand/od_configs.json
  python3 build_od_configs.py write   the same, then work/conf_clean/<day>.json for every day (only if the test passes)
  python3 build_od_configs.py intra   work/conf_intra/<day>.json: conf_clean plus the intra-municipal trips of the active municipalities
The summed cells are cached in $SIM_RUNS/od_cells_cache.pkl (proprietary, outside the repository).
"""
import json
import os
import pickle
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import demand_scaling as D  # noqa: E402
from paths import ROOT  # noqa: E402

TABLES = ROOT / "data/tables_rpc-rpc"
CLEAN = D.RERUN / "work/conf_clean"
INTRA = D.RERUN / "work/conf_intra"
TEMPLATE = D.RERUN / "work/conf_noaug"
TEST_PERIOD = (date(2020, 1, 1), date(2020, 2, 29))
CLEAN_PERIOD = (date(2020, 1, 13), date(2020, 2, 23))
NAME = lambda s: str(s).replace(" ", "")  # noqa: E731
FOREIGN = "000000000"
NO_PROVINCE_COPY = bool(os.environ.get("NO_PROVINCE_COPY"))  # model v2: cells of a province relation stay out of the random-end classes (model/submission/FINAL_MODEL_AUDIT.md)


def read_cells(day_hour):
    """Non-zero cells of one table: arrays of origin id, destination id, count."""
    day, h = day_hour
    x = pd.read_csv(TABLES / f"{day:%y%m%d}{h:02d}00.csv", sep=";", header=[0, 1], index_col=[0, 1, 2], low_memory=False)
    x = x[~x.index.get_level_values(1).isna()]
    o = x.index.get_level_values(1).astype(int).astype(str).str.zfill(9).to_numpy()
    names = dict(zip(o, x.index.get_level_values(2)))
    cols = [str(c)[-9:].zfill(9) for c in x.columns.get_level_values(0)]
    v = x.apply(pd.to_numeric, errors="coerce").fillna(0).to_numpy()
    i, j = np.nonzero(v)
    return day, h, o[i], np.array(cols)[j], v[i, j], names


def accumulate(periods):
    """{period: {(weekday, hour): DataFrame of summed cells}}, {period: {weekday: number of days}}."""
    days = sorted({periods[p][0] + timedelta(i) for p in periods
                   for i in range((periods[p][1] - periods[p][0]).days + 1)})
    sums = {p: defaultdict(list) for p in periods}
    names = {}
    with ProcessPoolExecutor(4) as ex:
        for day, h, o, d, v, nm in ex.map(read_cells, [(x, h) for x in days for h in range(24)], chunksize=24):
            names.update(nm)
            f = pd.DataFrame({"o": o, "d": d, "v": v})
            for p, (a, b) in periods.items():
                if a <= day <= b:
                    sums[p][day.weekday(), h].append(f)
    n = {p: {w: sum(1 for x in days if periods[p][0] <= x <= periods[p][1] and x.weekday() == w) for w in range(7)} for p in periods}
    return {p: {k: pd.concat(v).groupby(["o", "d"]).v.sum() for k, v in s.items()} for p, s in sums.items()}, n, names


def rates(values):
    """Hourly values -> 96 quarter rates: round(v/4), then a zero takes the previous value."""
    q = np.round(np.asarray(values, float) / 4)
    for h in range(1, 24):
        if q[h] == 0:
            q[h] = q[h - 1]
    return [int(v) for v in np.repeat(q, 4)]


def province_codes():
    g = pd.read_csv(ROOT / "vars/extra/italy_com.csv", sep=";", dtype=str)
    return {NAME(n): u[:6] for n, u in g.drop_duplicates("PRO_NAME")[["PRO_NAME", "UID"]].values}


def province_cells(o, d, relations):
    """Boolean mask of the cells (origin ids, destination ids) that belong to a province relation."""
    return np.array([x in relations for x in zip(o.str[:6], d.str[:6])], dtype=bool)


def build(template, by_hour, ndays, names):
    """Rates of every source of `template` for one weekday. by_hour: {hour: Series summed over ndays, index (o, d)}."""
    src = template["sources"]
    id_of = {}
    for k, v in names.items():
        id_of.setdefault(NAME(v), []).append(k)
    act = {}
    for k in src:
        if k.endswith("_dest_OUT"):
            n = NAME(k[:-9])
            ids = [i for i in id_of.get(n, []) if i.startswith("008")] or id_of.get(n, [])
            assert len(ids) == 1, (n, ids)
            act[n] = ids[0]
    act_ids = set(act.values())
    prov = province_codes()
    prov_ids = {n: c for n, c in prov.items()}
    relations = {tuple(prov_ids[x] for x in k[:-3].split("_")) for k, c in src.items() if "scr_dest_prov" in c["pawns"]}
    out = {k: np.zeros(24) for k in src}
    for h in range(24):
        s = by_hour[h]
        cells = (s / ndays).astype(int)  # as od-model.py
        cells = cells[cells > 0].reset_index()
        cells.columns = ["o", "d", "v"]
        oa, da = cells.o.isin(act_ids), cells.d.isin(act_ids)
        free = ~province_cells(cells.o, cells.d, relations) if NO_PROVINCE_COPY else np.ones(len(cells), dtype=bool)
        dest = cells[~oa & da & free].groupby("d").v.sum()
        orig = cells[oa & ~da & free].groupby("o").v.sum()
        pairs = cells[oa & da].set_index(["o", "d"]).v
        pv = (s.groupby([s.index.get_level_values(0).str[:6], s.index.get_level_values(1).str[:6]]).sum() / ndays).astype(int)
        locals_ = cells[~oa & ~da & free].v.sum()
        for k, c in src.items():
            kind = next(iter(c["pawns"]))
            if kind == "rnd_rnd":
                out[k][h] = locals_
            elif kind == "rnd_dest":
                out[k][h] = dest.get(act[NAME(k[:-9])], 0)
            elif kind == "src_rnd":
                out[k][h] = orig.get(act[NAME(k[:-7])], 0)
            else:
                a, b = k[:-3].split("_")
                if kind == "scr_dest":
                    out[k][h] = pairs.get((act[a], act[b]), 0)
                else:
                    out[k][h] = pv.get((prov_ids[a], prov_ids[b]), 0)
    return {k: rates(v) for k, v in out.items()}


def compare(template, built):
    rows = []
    for k, c in template["sources"].items():
        a, b = np.array(c["creation_rate"]), np.array(built[k])
        rows.append((next(iter(c["pawns"])), int((a == b).sum()), a.size, int(np.abs(a - b).sum()), int(a.sum()), bool((a == b).all())))
    r = pd.DataFrame(rows, columns=["cls", "same", "n", "abs", "total", "full"])
    g = r.groupby("cls").agg(sources=("full", "size"), identical_sources=("full", "sum"), same=("same", "sum"), n=("n", "sum"), abs=("abs", "sum"), total=("total", "sum"))
    g["exact_pct"] = (100 * g.same / g.n).round(3)
    g["abs_over_total_pct"] = (100 * g["abs"] / g.total.clip(lower=1)).round(3)
    return g.drop(columns=["same", "n"]).to_dict("index")


def write_intra():
    """conf_intra/<day>.json: conf_clean plus one source per active municipality for its intra-municipal trips (class intra)."""
    sums, n, names = pickle.load(open(D.RUNS / "od_cells_cache.pkl", "rb"))
    id_of = {}
    for k, v in names.items():
        id_of.setdefault(NAME(v), []).append(k)
    INTRA.mkdir(parents=True, exist_ok=True)
    report = {}
    for day in D.DAYS[2020] + D.DAYS[2021]:
        wd = pd.Timestamp(day).weekday()
        c = json.load(open(CLEAN / f"{day}.json"))
        total = 0
        for k in [x for x in c["sources"] if x.endswith("_src_IN")]:
            nm = NAME(k[:-7])
            ids = [i for i in id_of.get(nm, []) if i.startswith("008")] or id_of.get(nm, [])
            assert len(ids) == 1, (nm, ids)
            v = [int(sums["clean"][wd, h].get((ids[0], ids[0]), 0) / n["clean"][wd]) for h in range(24)]  # truncated as od-model.py
            s = json.loads(json.dumps(c["sources"][k]))
            s["pawns"] = {"intra": s["pawns"]["src_rnd"]}
            s["creation_rate"] = rates(v)
            c["sources"][f"{nm}_intra_IN"] = s
            total += sum(s["creation_rate"])
        report[day] = {"intra_agents": total, "existing_agents": sum(sum(s["creation_rate"]) for k, s in c["sources"].items() if "_intra_" not in k)}
        json.dump(c, open(INTRA / f"{day}.json", "w"))
    (D.RES / "od_intra.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({d: report[d] for d in ("2020-02-10", "2020-02-15")}))


def main():
    periods = {"test": TEST_PERIOD, "clean": CLEAN_PERIOD}
    cache = D.RUNS / "od_cells_cache.pkl"
    if cache.is_file():
        sums, n, names = pickle.load(open(cache, "rb"))
    else:
        sums, n, names = accumulate(periods)
        pickle.dump((sums, n, names), open(cache, "wb"))
    report = {"test_period": [str(x) for x in TEST_PERIOD], "clean_period": [str(x) for x in CLEAN_PERIOD],
              "days_by_weekday": {p: n[p] for p in n}, "test": {}, "clean_vs_existing_agents": {}}
    clean = {}
    for day in D.WEEK:
        wd = pd.Timestamp(day).weekday()
        tpl = json.load(open(TEMPLATE / f"{day}.json"))
        by = {p: {h: sums[p][wd, h] for h in range(24)} for p in periods}
        t = build(tpl, by["test"], n["test"][wd], names)
        report["test"][day] = compare(tpl, t)
        c = clean[wd] = build(tpl, by["clean"], n["clean"][wd], names)
        before, after = sum(sum(s["creation_rate"]) for s in tpl["sources"].values()), sum(sum(v) for v in c.values())
        report["clean_vs_existing_agents"][day] = {"existing": before, "clean": after, "ratio": round(after / before, 4)}
    (D.RES / "od_configs.json").write_text(json.dumps(report, indent=1, default=int) + "\n")
    print(json.dumps(report, indent=1, default=int))
    if sys.argv[1:] == ["write"]:
        passed = all(v["identical_sources"] == v["sources"] for t in report["test"].values() for v in t.values())
        assert passed, "acceptance test not passed: configurations not written"
        CLEAN.mkdir(parents=True, exist_ok=True)
        for day in D.DAYS[2020] + D.DAYS[2021]:
            tpl = json.load(open(TEMPLATE / f"{day}.json"))
            for k, v in clean[pd.Timestamp(day).weekday()].items():
                tpl["sources"][k]["creation_rate"] = v
            json.dump(tpl, open(CLEAN / f"{day}.json", "w"))
        print("written to", CLEAN)


if __name__ == "__main__":
    write_intra() if sys.argv[1:] == ["intra"] else main()
