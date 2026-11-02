#!/usr/bin/env python3
"""Audit: trips of the neighbouring-province relations also counted in the classes with a random end. The frozen model is not changed.

build_od_configs.build computes the province relations from all cells, and the classes rnd_rnd, rnd_dest and src_rnd from the same cells,
without removing them. Two audit arms, same k, factors, routing and seed as the frozen model, Monday and Saturday:
  no_province_class : without scr_dest_prov
  no_random_copy    : scr_dest_prov kept, its cells removed from the random-end classes
Exploratory: added after the suspicion arose, no rule, k not retuned, outputs in $SIM_RUNS/province_duplication. Reported, not adopted.
Audit of model v1: run it from the tag frozen-v1, on sim_runs_nocode2.

  python3 od_province_duplication.py count | jobs | one ARM DAY | evaluate -> model/results/demand/province_duplication.json
"""
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_od_configs as B  # noqa: E402
import calibrate_demand as C  # noqa: E402
import demand_scaling as D  # noqa: E402
import od_factor_decomposition as OD  # noqa: E402
import source_value as V  # noqa: E402

OUT = D.RUNS / "province_duplication"
ARMS = ("no_province_class", "no_random_copy")
N_BOOT, SEED = 2000, 20261113
TEMPLATE = D.RERUN / "work/conf_noaug"
PROV = "scr_dest_prov"


def cache():
    return pickle.load(open(D.RUNS / "od_cells_cache.pkl", "rb"))


def province_pairs(src):
    code = B.province_codes()
    return {(code[a], code[b]) for a, b in (k[:-3].split("_") for k, v in src.items() if PROV in v["pawns"])}


def split_cells(s, pairs):
    """Boolean mask of the cells of a province relation."""
    o, d = s.index.get_level_values(0).str[:6], s.index.get_level_values(1).str[:6]
    return np.array([x in pairs for x in zip(o, d)])


def filtered(wd, sums, n, drop=None):
    """Cells by hour without the code, as remove_od_code.py, and optionally without the cells of the province relations."""
    by = {}
    for h in range(24):
        s = sums["clean"][wd, h]
        s = s[(s.index.get_level_values(1) != B.FOREIGN) & (s.index.get_level_values(0) != B.FOREIGN)]
        by[h] = s[~split_cells(s, drop)] if drop else s
    return by


def rates_without_copy(day):
    """Sources of the final demand with the copy removed from the random-end classes; other classes as in the final demand."""
    sums, n, names = cache()
    wd = pd.Timestamp(day).weekday()
    conf = json.load(open(D.CONF / f"{day}.json"))
    built = B.build(conf, filtered(wd, sums, n, province_pairs(conf["sources"])), n["clean"][wd], names)
    for k, s in conf["sources"].items():
        if next(iter(s["pawns"])) in ("rnd_rnd", "rnd_dest", "src_rnd"):
            s["creation_rate"] = built[k]
    return conf["sources"]


def count():
    sums, n, names = cache()
    out = {}
    for day in D.WEEK:
        wd = pd.Timestamp(day).weekday()
        conf = json.load(open(D.CONF / f"{day}.json"))["sources"]
        rebuilt = B.build(json.load(open(D.CONF / f"{day}.json")), filtered(wd, sums, n), n["clean"][wd], names)
        reproduced = all(rebuilt[k] == v["creation_rate"] for k, v in conf.items())
        without = rates_without_copy(day)
        by = lambda src: {c: sum(sum(v["creation_rate"]) for v in src.values() if c in v["pawns"]) for c in D.CLASSES}
        a, b = by(conf), by(without)
        total = sum(a.values())
        out[day] = {"conf_reproduced_by_generator": reproduced, "province_sources": sum(PROV in v["pawns"] for v in conf.values()), "agents_k1": a, "agents_k1_no_random_copy": b,
                    "copy_in_random_classes": {c: a[c] - b[c] for c in ("rnd_rnd", "rnd_dest", "src_rnd")}, "province_share_of_agents": a[PROV] / total, "copy_share_of_agents": sum(a[c] - b[c] for c in ("rnd_rnd", "rnd_dest", "src_rnd")) / total, "total_agents_k1": total}
        print(day, json.dumps(out[day]), flush=True)
    legacy = {}
    for day in ("2020-02-10", "2020-02-15"):
        wd = pd.Timestamp(day).weekday()
        tpl = json.load(open(TEMPLATE / f"{day}.json"))
        built = B.build(tpl, {h: sums["test"][wd, h] for h in range(24)}, n["test"][wd], names)
        legacy[day] = {"legacy_conf_reproduced": all(built[k] == v["creation_rate"] for k, v in tpl["sources"].items()), "province_agents": sum(sum(v["creation_rate"]) for v in tpl["sources"].values() if PROV in v["pawns"])}
    out["legacy_generator"] = legacy
    print(legacy)
    D.RES.joinpath("province_duplication_count.json").write_text(json.dumps(out, indent=1) + "\n")


def base(arm, day):
    return OUT / arm / f"sim_{D.tag(day)}"


def sources(arm, day):
    k = D.k_of(day)
    src = rates_without_copy(day) if arm == "no_random_copy" else json.load(open(D.CONF / f"{day}.json"))["sources"]
    if arm == "no_province_class":
        src = {a: b for a, b in src.items() if PROV not in b["pawns"]}
    for s in src.values():
        s["creation_rate"] = [int(round(k * v)) for v in s["creation_rate"]]
    return D.province_scaled(src)


def jobs():
    for a in ARMS:
        for d in C.CAL_DAYS:
            if not list(base(a, d).parent.glob(f"sim_{D.tag(d)}_uniq_*.csv")):
                print(a, d)


def one(arm, day):
    c = D.v6_config(day, D.VARIANTS["V6_scaled"], sources(arm, day), base(arm, day))
    res = D.run(c, base(arm, day))
    print(*res, flush=True)
    sys.exit(1 if res[1] else 0)


def evaluate():
    rng = np.random.default_rng(SEED)
    out = {}
    for day in C.CAL_DAYS:
        out[day] = {}
        for name, t in V.sets(day).items():
            o = t.obs.values
            frozen = V.daily(D.OUT / "V6_scaled", day, t.poly_lid)
            out[day][name] = {"frozen_volume_ratio": float(frozen.sum() / o.sum())}
            for arm in ARMS:
                s = V.daily(base(arm, day).parent, day, t.poly_lid)
                ok = (s > 0) & (frozen > 0)
                x = OD.compare(s, frozen, o, rng)
                x.update(volume_ratio=float(s.sum() / o.sum()), median_abs_log10_change=float(np.median(np.abs(np.log10(s[ok] / frozen[ok])))), max_abs_log10_change=float(np.abs(np.log10(s[ok] / frozen[ok])).max()))
                out[day][name][arm] = x
    D.RES.joinpath("province_duplication.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    {"count": count, "jobs": jobs, "evaluate": evaluate}[sys.argv[1]]() if len(sys.argv) == 2 else one(sys.argv[2], sys.argv[3])
