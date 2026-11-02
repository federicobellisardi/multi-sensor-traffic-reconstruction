#!/usr/bin/env python3
"""Demand configurations without the destination code 000000000: same generator and template as conf_clean.

  python3 remove_od_code.py   -> $DEMAND_CONF/<day>.json, model/results/demand/remove_od_code.json
"""
import json
import pickle
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_od_configs as B  # noqa: E402
import demand_scaling as D  # noqa: E402

CLEAN = D.RERUN / "work/conf_clean"


def main():
    assert D.NO_CODE and D.CONF != CLEAN, "source hpc/config.sh first"
    sums, n, names = pickle.load(open(D.RUNS / "od_cells_cache.pkl", "rb"))
    clean = {}
    rep = {}
    for day in D.WEEK:
        wd = pd.Timestamp(day).weekday()
        tpl = json.load(open(CLEAN / f"{day}.json"))
        by = {}
        for h in range(24):
            s = sums["clean"][wd, h]
            by[h] = s[(s.index.get_level_values(1) != B.FOREIGN) & (s.index.get_level_values(0) != B.FOREIGN)]
        clean[wd] = B.build(tpl, by, n["clean"][wd], names)
        cls = {}
        for k, c in tpl["sources"].items():
            a = next(iter(c["pawns"]))
            x = cls.setdefault(a, [0, 0])
            x[0] += sum(c["creation_rate"])
            x[1] += sum(clean[wd][k])
        rep[day] = cls
    assert D.NO_CODE and D.CONF != CLEAN, "source hpc/config.sh first"
    D.CONF.mkdir(parents=True, exist_ok=True)
    for day in D.DAYS[2020] + D.DAYS[2021]:
        tpl = json.load(open(CLEAN / f"{day}.json"))
        for k, v in clean[pd.Timestamp(day).weekday()].items():
            tpl["sources"][k]["creation_rate"] = v
        json.dump(tpl, open(D.CONF / f"{day}.json", "w"))
    (D.RES / "remove_od_code.json").write_text(json.dumps(rep, indent=1) + "\n")
    for d in ("2020-02-10", "2020-02-15"):
        print(d, rep[d], "total", sum(v[0] for v in rep[d].values()), sum(v[1] for v in rep[d].values()))


if __name__ == "__main__":
    main()
