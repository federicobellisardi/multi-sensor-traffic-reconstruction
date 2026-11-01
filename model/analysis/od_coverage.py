#!/usr/bin/env python3
"""How much of the OD matrix reaches the simulation with its relation, by class (Monday and Saturday, clean period).

Aggregate shares only; the cached cells are proprietary and stay outside the repository.

  python3 od_coverage.py -> model/results/demand/od_coverage.json
"""
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_od_configs as B  # noqa: E402
import demand_scaling as D  # noqa: E402

DAYS = {"Monday": "2020-02-10", "Saturday": "2020-02-15"}


def one(day, sums, n, names):
    wd = pd.Timestamp(day).weekday()
    c = json.load(open(B.CLEAN / f"{day}.json"))["sources"]
    id_of = {}
    for k, v in names.items():
        id_of.setdefault(B.NAME(v), []).append(k)
    act = {}
    for k in c:
        if k.endswith("_src_IN"):
            m = B.NAME(k[:-7])
            act[m] = ([i for i in id_of.get(m, []) if i.startswith("008")] or id_of[m])[0]
    ids = set(act.values())
    tmpl = {(act[a], act[b]) for a, b in (k[:-3].split("_") for k, v in c.items() if "scr_dest" in v["pawns"])}
    raw = pd.concat([sums["clean"][wd, h] / n["clean"][wd] for h in range(24)]).groupby(level=[0, 1]).sum()
    kept = pd.concat([(sums["clean"][wd, h] / n["clean"][wd]).astype(int) for h in range(24)]).groupby(level=[0, 1]).sum()
    res = {"municipalities_in_table": int(len(set(raw.index.get_level_values(0)) | set(raw.index.get_level_values(1)))), "active_municipalities": len(ids),
           "relations_nonzero": int((raw > 0).sum()), "relations_located": len(tmpl)}
    o, d = raw.index.get_level_values(0), raw.index.get_level_values(1)
    oa, da, same = o.isin(ids), d.isin(ids), o == d
    pair = pd.Series([x in tmpl for x in raw.index], index=raw.index)
    total = raw.sum()
    res["share_of_table"] = {"intra_municipal": float(raw[same].sum() / total),
                             "located_relations_both_ends": float(raw[pair.values].sum() / total),
                             "active_to_active_not_located": float(raw[oa & da & ~same & ~pair.values].sum() / total),
                             "active_origin_only": float(raw[oa & ~da].sum() / total), "active_destination_only": float(raw[~oa & da].sum() / total),
                             "both_ends_outside_active_inter_municipal": float(raw[~oa & ~da & ~same].sum() / total)}
    res["table_total_per_day"] = float(total)
    res["lost_to_integer_truncation_share"] = float(1 - kept.sum() / total)
    res["agents_injected_k1"] = {next(iter(v["pawns"])): 0 for v in c.values()}
    for v in c.values():
        res["agents_injected_k1"][next(iter(v["pawns"]))] += int(sum(v["creation_rate"]))
    nonintra = raw[~same]
    res["share_nonintra_with_relation_kept"] = float(raw[pair.values & ~same].sum() / nonintra.sum())
    return res


def main():
    sums, n, names = pickle.load(open(D.RUNS / "od_cells_cache.pkl", "rb"))
    out = {k: one(d, sums, n, names) for k, d in DAYS.items()}
    (D.RES / "od_coverage.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
