#!/usr/bin/env python3
"""Rebuild the polyline geometry of the simulation graph from the minimocas cartography.

Input : vars/carto/er-speed.pro and er-speed.pnt (commit a059fb0, 2024-05-20: 3,925 polylines),
        the cartography used by all Article 1 simulations.
        .pnt format: header "<poly_cid> <skip> <npoints>" then npoints lines "<lat*1e6> <lon*1e6>".
Output: article1/results/carto_a059fb0.geojson with poly_cid, nF, nT, length, speed, oneway.
"""
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString

A1 = Path(__file__).resolve().parents[1]
ROOT = A1.parent
CARTO = ROOT / "vars/carto"


def main():
    pro = pd.read_csv(CARTO / "er-speed.pro", sep=r"\s+", header=None, skiprows=1, usecols=range(10),
                      names=["poly_cid", "nF", "nT", "length", "lvl_ps", "a", "b", "c", "speed", "oneway"])
    geoms = {}
    with open(CARTO / "er-speed.pnt") as f:
        while True:
            head = f.readline().split()
            if not head:
                break
            cid, n = int(head[0]), int(head[2])
            pts = [tuple(map(int, f.readline().split())) for _ in range(n)]
            geoms[cid] = LineString([(lon / 1e6, lat / 1e6) for lat, lon in pts])
    pro["geometry"] = pro.poly_cid.map(geoms)
    assert pro.geometry.notna().all(), "polyline without points"
    g = gpd.GeoDataFrame(pro.drop(columns=["a", "b", "c"]), crs=4326)
    L = g.to_crs(32632).length
    print(len(g), "polylines; max |geometric - declared length| =", float((L - g["length"]).abs().max()), "m")
    g.to_file(A1 / "results/carto_a059fb0.geojson", driver="GeoJSON")


if __name__ == "__main__":
    main()
