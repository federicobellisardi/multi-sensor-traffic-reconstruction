#!/usr/bin/env python3
"""Numbers on the ranking of the municipalities and on the demand classes of the N grid, for the text. No simulation.

Cumulative share of inter-municipal trips in and out, without destination code 000000000, and agents by class on the Monday.

  python3 od_matrix_summary.py -> model/results/demand/od_matrix_summary.json
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_od_configs as B  # noqa: E402
import calibrate_demand as C  # noqa: E402
import demand_scaling as D  # noqa: E402
import od_matrix as M  # noqa: E402

RANDOM = ("src_rnd", "rnd_dest", "rnd_rnd")


def shares(src):
    t = {}
    for v in src.values():
        k = next(iter(v["pawns"]))
        t[k] = t.get(k, 0) + sum(v["creation_rate"])
    return {"agents": int(sum(t.values())), "random_share": sum(t.get(k, 0) for k in RANDOM) / sum(t.values())}


def main():
    sums, _, _ = M.cache()
    x = pd.concat(list(sums["clean"].values())).groupby(level=[0, 1]).sum()
    x = x[(x.index.get_level_values(0) != x.index.get_level_values(1)) & (x.index.get_level_values(1) != B.FOREIGN)]
    io = x.groupby(level=0).sum().add(x.groupby(level=1).sum(), fill_value=0)
    v = io[io.index.isin(M.COM.index[M.COM.REG == 8])].sort_values(ascending=False).values
    cum = np.cumsum(v) / v.sum()
    day = C.CAL_DAYS[0]
    frozen = json.load(open(M.FROZEN / f"k{D.k_of(day):.1f}" / f"sim_{D.tag(day)}.json"))["sources"]
    res = {"municipalities": int(len(v)), "cumulative_activity": {str(n): float(cum[n - 1]) for n in (50, 100, 150, 200, 250, 300)},
           "knee_cumulative_activity": int(np.argmax(cum - np.arange(len(v)) / (len(v) - 1))) + 1,
           "classes_monday": {"frozen": shares(frozen)} | {n: shares(M.sources(n, day)[0]) for n in ("N100_r20_x", "N347_r20_x", "N347_r20")}}
    (D.RES / "od_matrix_summary.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
