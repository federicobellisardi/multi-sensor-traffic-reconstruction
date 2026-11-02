#!/usr/bin/env python3
"""Exploratory: distance of the OD tables against agent-km of the simulation, Monday -> results/experiments/od_trip_length.json

Distances are straight lines between municipal centres. Agent-km come from the hourly `_pawn_` snapshots, so they are estimates.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_od_configs as B  # noqa: E402
import demand_scaling as D  # noqa: E402
import od_matrix as M  # noqa: E402
import od_pairing as P  # noqa: E402
from paths import RESULTS as R1  # noqa: E402


def od_distances():
    sums, cnt, _ = M.cache()
    s = pd.concat([sums["clean"][0, h] / cnt["clean"][0] for h in range(24)]).groupby(level=[0, 1]).sum()
    z = s[s.index.get_level_values(1) != B.FOREIGN].rename("v").reset_index()
    z.columns = ["o", "d", "v"]
    z = z[z.o.isin(M.COM.index) & z.d.isin(M.COM.index) & (z.o != z.d)].copy()
    la, lo, lb, lp = (np.radians(M.COM[c].reindex(x).values) for c, x in (("LAT", z.o), ("LON", z.o), ("LAT", z.d), ("LON", z.d)))
    z["km"] = 2 * 6371 * np.arcsin(np.sqrt(np.sin((lb - la) / 2) ** 2 + np.cos(la) * np.cos(lb) * np.sin((lp - lo) / 2) ** 2))
    z = z.sort_values("km")
    q = z.v.cumsum() / z.v.sum()
    return {"trips": float(z.v.sum()), "mean_km": float(np.average(z.km, weights=z.v)), "median_km": float(z.km[q >= 0.5].iloc[0]), "q90_km": float(z.km[q >= 0.9].iloc[0]), "share_below_25km": float(z.v[z.km < 25].sum() / z.v.sum())}


def agent_km(folder):
    day = "2020-02-10"
    cfg = json.load(open(folder / f"sim_{D.tag(day)}.json"))["sources"]
    agents = {}
    for s in cfg.values():
        t = next(iter(s["pawns"]))
        agents[t] = agents.get(t, 0) + sum(s["creation_rate"])
    d = pd.read_csv(next(folder.glob(f"sim_{D.tag(day)}_pawn_*.csv")), sep=";", usecols=["tag", "timestamp", "speed"])
    step = int(np.median(np.diff(np.sort(d.timestamp.unique()))))
    km = d.assign(a=d.speed.abs()).groupby("tag").a.sum() * step / 1000
    return {"km_by_class": km.to_dict(), "agents_by_class": agents, "km_per_agent_by_class": {t: float(km[t] / agents[t]) for t in km.index}, "km_per_agent": float(km.sum() / sum(agents.values()))}


if __name__ == "__main__":
    res = {"od_between_municipalities": od_distances(), "model": agent_km(D.RUNS / "final_q15"), "N347": agent_km(P.OUT / "N347_real_s1")}
    (R1 / "experiments/od_trip_length.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))
