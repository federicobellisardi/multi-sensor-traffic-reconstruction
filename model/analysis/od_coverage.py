#!/usr/bin/env python3
"""How much of the OD table reaches the simulation with its relation, in trips and in relations (Monday and Saturday, final demand).

Aggregate shares only; the cached cells are proprietary and stay outside the repository. The relation counts as kept if its
source injects agents in the final demand (hpc/config.sh, $DEMAND_CONF). The version with the code 000000000 in the demand is kept in
demand/od_coverage_with_code_20261031.json.

  python3 od_coverage.py -> model/results/demand/od_coverage.json
"""
import json
import pickle
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_od_configs as B  # noqa: E402
import demand_scaling as D  # noqa: E402

DAYS = {"Monday": "2020-02-10", "Saturday": "2020-02-15"}


def one(day, sums, n, names):
    wd = pd.Timestamp(day).weekday()
    c = json.load(open(D.CONF / f"{day}.json"))["sources"]
    id_of = {}
    for k, v in names.items():
        id_of.setdefault(B.NAME(v), []).append(k)
    act = {}
    for k in c:
        if k.endswith("_src_IN"):
            m = B.NAME(k[:-7])
            act[m] = ([i for i in id_of.get(m, []) if i.startswith("008")] or id_of[m])[0]
    ids = set(act.values())
    kept_pairs = {(act[a], act[b]) for a, b in (k[:-3].split("_") for k, v in c.items() if "scr_dest" in v["pawns"] and sum(v["creation_rate"]) > 0)}
    raw = pd.concat([sums["clean"][wd, h] / n["clean"][wd] for h in range(24)]).groupby(level=[0, 1]).sum()
    o, d = raw.index.get_level_values(0), raw.index.get_level_values(1)
    code, same, oa, da = (o == B.FOREIGN) | (d == B.FOREIGN), o == d, o.isin(ids), d.isin(ids)
    pair = pd.Series([x in kept_pairs for x in raw.index], index=raw.index).values
    rest = ~code & ~same
    classes = {"code_000000000": code, "intra_active_discarded": ~code & same & oa, "intra_other_random_both_ends": ~code & same & ~oa,
               "relation_kept": rest & pair, "active_to_active_lost_to_rounding": rest & oa & da & ~pair,
               "active_origin_random_destination": rest & oa & ~da, "active_destination_random_origin": rest & ~oa & da, "both_outside_random_both_ends": rest & ~oa & ~da}
    total = raw.sum()
    res = {"table_trips_per_day": float(total), "relations_nonzero": int(len(raw)), "active_municipalities": len(ids),
           "classes": {k: {"trips": float(raw[m].sum()), "share_of_table": float(raw[m].sum() / total), "relations": int(m.sum())} for k, m in classes.items()}}
    inter = raw[~same]
    res["inter_municipal_with_code"] = {"trips": float(inter.sum()), "relations": int(len(inter)), "share_relation_kept": float(raw[rest & pair].sum() / inter.sum()),
                                        "share_code": float(raw[code & ~same].sum() / inter.sum()), "share_relation_not_used": float(raw[rest & ~pair].sum() / inter.sum())}
    res["inter_municipal_without_code"] = {"trips": float(raw[rest].sum()), "relations": int(rest.sum()), "share_trips_relation_kept": float(raw[rest & pair].sum() / raw[rest].sum()), "share_relations_kept": float((rest & pair).sum() / rest.sum())}
    agents = {}
    for v in c.values():
        agents[next(iter(v["pawns"]))] = agents.get(next(iter(v["pawns"])), 0) + int(sum(v["creation_rate"]))
    res["agents_k1"] = agents
    return res


def main():
    sums, n, names = pickle.load(open(D.RUNS / "od_cells_cache.pkl", "rb"))
    out = {k: one(d, sums, n, names) for k, d in DAYS.items()}
    (D.RES / "od_coverage.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
