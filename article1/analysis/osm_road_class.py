#!/usr/bin/env python3
"""Assign an OpenStreetMap road class (and ref) to every model polyline.

Source: Geofabrik extract europe/italy/nord-est-261026.osm.pbf (ODbL, OpenStreetMap
contributors), cached in /home/fede/data_cache/osm/ (see manifest.txt there).
For each polyline, three points at 25/50/75 % of its length are matched to the nearest OSM
way of class motorway..unclassified within 30 m; the class is the majority over matched points
(ties broken by the higher class), *_link ways are merged with their parent class.

Output: article1/results/road_class.csv (poly_cid, road_class, ref, n_matched).
"""
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio

A1 = Path(__file__).resolve().parents[1]
ROOT = A1.parent
PBF = Path("/home/fede/data_cache/osm/nord-est-261026.osm.pbf")
CACHE = PBF.with_name("er_main_roads_261026.gpkg")
CARTO = A1 / "results/carto_a059fb0.geojson"
CLASSES = ["motorway", "trunk", "primary", "secondary", "tertiary", "unclassified"]
CRS = 32632


def main():
    carto = gpd.read_file(CARTO)
    if CACHE.exists():
        osm = gpd.read_file(CACHE)
    else:
        bbox = tuple(carto.total_bounds + np.array([-0.05, -0.05, 0.05, 0.05]))
        hw = "', '".join(CLASSES + [c + "_link" for c in CLASSES[:5]])
        osm = pyogrio.read_dataframe(PBF, layer="lines", bbox=bbox, columns=["highway", "name", "other_tags"],
                                     where=f"highway IN ('{hw}')")
        osm["road_class"] = osm.highway.str.replace("_link", "", regex=False)
        osm["ref"] = osm.other_tags.fillna("").str.extract(r'"ref"=>"([^"]+)"', expand=False)
        osm = osm.to_crs(CRS)[["road_class", "ref", "name", "geometry"]]
        osm.to_file(CACHE, driver="GPKG")
    print("OSM ways", len(osm), osm.road_class.value_counts().to_dict())
    c = carto.to_crs(CRS)
    pts = []
    for f in (0.25, 0.5, 0.75):
        p = c.copy()
        p["geometry"] = c.geometry.interpolate(f, normalized=True)
        pts.append(p[["poly_cid", "geometry"]])
    pts = gpd.GeoDataFrame(pd.concat(pts, ignore_index=True), crs=CRS)
    j = gpd.sjoin_nearest(pts, osm, max_distance=30, distance_col="d").sort_values("d")
    j = j[~j.index.duplicated()]
    rank = {k: i for i, k in enumerate(CLASSES)}
    j["rank"] = j.road_class.map(rank)
    out = []
    for pc, g in j.groupby("poly_cid"):
        cnt = g.road_class.value_counts()
        best = sorted(cnt.index, key=lambda k: (-cnt[k], rank[k]))[0]
        refs = g.loc[g.road_class == best, "ref"].dropna()
        out.append((pc, best, refs.mode().iloc[0] if len(refs) else "", len(g)))
    res = pd.DataFrame(out, columns=["poly_cid", "road_class", "ref", "n_matched"])
    res = carto[["poly_cid"]].merge(res, how="left").fillna({"road_class": "unmatched", "ref": "", "n_matched": 0})
    res.to_csv(A1 / "results/road_class.csv", index=False)
    print(res.road_class.value_counts().to_dict())
    L = carto.set_index("poly_cid")["length"]
    print("length share (km):", (res.set_index("poly_cid").join(L).groupby("road_class")["length"].sum() / 1000).round(0).to_dict())


if __name__ == "__main__":
    main()
