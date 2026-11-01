#!/usr/bin/env python3
"""Profile error on GPS links as a function of network distance from the nearest detector.

Network distance = minimum number of polylines between a GPS-matched polyline and any polyline
carrying an MTS detector (undirected adjacency of the project cartography, breadth-first search).
For each distance class the median hourly-share MAE of the raw and of the assimilated
reconstruction is reported (link metrics from reconstruct_and_validate.py validate).

Usage: python3 model/analysis/distance_to_detector.py
Output: model/results/corrected/error_vs_detector_distance.csv
"""
from collections import deque
from pathlib import Path

import pandas as pd
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import ROOT, RESULTS as R1  # noqa: E402



def hop_distance():
    pro = pd.read_csv(ROOT / "vars/carto/er-speed.pro", sep=r"\s+", header=None, skiprows=1, usecols=[0, 1, 2],
                      names=["poly_cid", "nF", "nT"])
    pro["poly_lid"] = range(len(pro))
    by_node = {}
    for cid, a, b in pro[["poly_cid", "nF", "nT"]].values:
        by_node.setdefault(a, []).append(cid)
        by_node.setdefault(b, []).append(cid)
    nbr = {cid: set(by_node[a] + by_node[b]) - {cid} for cid, a, b in pro[["poly_cid", "nF", "nT"]].values}
    bar = pd.read_csv(ROOT / "vars/extra/er_barriers_cartodata.csv", sep=";")
    lid2cid = dict(zip(pro.poly_lid, pro.poly_cid))
    src = {lid2cid[l] for l in bar.poly_lid}
    dist = {c: 0 for c in src}
    q = deque(src)
    while q:
        c = q.popleft()
        for n in nbr[c]:
            if n not in dist:
                dist[n] = dist[c] + 1
                q.append(n)
    return pd.Series(dist, name="hops")


def main():
    h = hop_distance()
    rows = []
    for year in (2020, 2021):
        m = pd.read_csv(R1 / f"private/corrected_link_metrics_{year}_all.csv").set_index("cid")
        m = m.join(h)
        m["hop_class"] = pd.cut(m.hops, [-1, 0, 1, 2, 3, 5, 1000], labels=["0", "1", "2", "3", "4-5", "6+"])
        g = m.groupby("hop_class", observed=True).agg(links=("mae_pp", "size"), mae_raw=("mae_pp_raw", "median"),
                                                     mae_assim=("mae_pp", "median"))
        g["gain_pp"] = g.mae_raw - g.mae_assim
        g["year"] = year
        rows.append(g.reset_index())
    out = pd.concat(rows)
    out.to_csv(R1 / "corrected/error_vs_detector_distance.csv", index=False)
    print(out.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
