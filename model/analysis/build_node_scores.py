#!/usr/bin/env python3
"""Node scores for the random origin/destination draws of minimocas (file_score_pop), from the ISTAT 2021 population.

The score of a node is the population (POP21) of the census sections whose representative point is closer to that
node than to any other node (Voronoi cell of the node on the road network). The population of Emilia-Romagna is
conserved; nodes outside the region get only the sections that are nearest to them (often none, score 0, so they
are never drawn as random origin or destination).

The previous vars/extra/ace_score.csv cannot be used: all scores are inf and it is not consistent with the
current network (node_lid up to 2703 for a network of 2548 nodes, repeated node_lid).

Node ids: minimocas numbers the nodes (lid) by increasing cid; the cid of the nodes and their coordinates are those
of the end points of the links in er-carto.geojson (checked on the source nodes of a simulation, error < 10 m).

  python3 build_node_scores.py --carto er-carto.geojson   -> vars/extra/node_score_pop2021.csv, summary on stdout
"""
import argparse
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

from paths import ROOT

CARTO = ROOT / "vars/extra"  # network of any simulation of the study (same er-carto.geojson)
SECTIONS = ROOT / "data/istat_2021/SHP/R08_21_WGS84.shp"
OUT = ROOT / "vars/extra/node_score_pop2021.csv"


def nodes(geojson):
    xy = {}
    for f in json.load(open(geojson))["features"]:
        p, c = f["properties"], f["geometry"]["coordinates"]
        xy[p["poly_nF"]] = tuple(c[0])
        xy[p["poly_nT"]] = tuple(c[-1])
    cids = sorted(xy)
    return pd.DataFrame({"node_cid": cids, "node_lid": range(len(cids)),
                         "lon": [xy[c][0] for c in cids], "lat": [xy[c][1] for c in cids]})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--carto", required=True, help="er-carto.geojson of a simulation")
    a = ap.parse_args()

    n = nodes(a.carto)
    pts = gpd.GeoDataFrame(n, geometry=gpd.points_from_xy(n.lon, n.lat), crs=4326).to_crs(32632)
    sec = gpd.read_file(SECTIONS)[["PRO_COM", "SEZ21_ID", "POP21", "geometry"]].to_crs(32632)

    rep = sec[sec.POP21 > 0].copy()
    rep["geometry"] = rep.geometry.representative_point()
    near = gpd.sjoin_nearest(rep, pts[["node_lid", "geometry"]], how="left", distance_col="d").drop_duplicates("SEZ21_ID")
    n["score"] = n.node_lid.map(near.groupby("node_lid").POP21.sum()).fillna(0.0)
    n["city"] = "ER"
    summary = {"nodes": int(len(n)), "population_total": float(sec.POP21.sum()), "population_assigned": float(n.score.sum()),
               "nodes_score_zero": int((n.score == 0).sum()),
               "sections_farther_than_5km_from_node": int((near.d > 5000).sum()),
               "population_farther_than_5km": float(near.POP21[near.d > 5000].sum()),
               "score_quantiles_0_25_50_75_100": [float(x) for x in np.quantile(n.score, [0, .25, .5, .75, 1])],
               "top5_share_of_population": float(n.score.nlargest(5).sum() / n.score.sum())}
    print(json.dumps(summary, indent=1))
    n[["node_cid", "node_lid", "score", "city"]].to_csv(OUT, sep=";", index=False)
    print("written", OUT)


if __name__ == "__main__":
    main()
