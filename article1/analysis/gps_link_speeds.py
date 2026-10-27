#!/usr/bin/env python3
"""Link speeds from raw Viasat GPS points (private vehicles, Forli-Cesena).

Each point with engine on, regular position fix (TIPO_POSIZIONE 9) and speed >= 5 km/h is
matched to the nearest model polyline within 20 m whose local bearing agrees with the
recorded heading within 30 degrees (either orientation). Outputs per polyline: number of
points, number of vehicles, median and 85th-percentile speed, overall and for off-peak
hours (10-15 h, weekdays).

Usage: python3 article1/analysis/gps_link_speeds.py 202002|202106
Output: article1/results/private/gps_link_speeds_<campaign>.csv (derived from proprietary data).
"""
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point

A1 = Path(__file__).resolve().parents[1]
ROOT = A1.parent
RAW = {"202002": "Forlì-Cesena_202002/VEM_FORLI_FEBBRAIO_GPSRAW_PRIVATEVEHICLES.csv",
       "202106": "Forlì-Cesena_202106/VEM_FORLI_GIUGNO_GPSRAW_PRIVATEVEHICLES.csv"}
CRS = 32632
MAXD, MAXANG = 20.0, 30.0


def bearing_at(lines, idx, pts):
    """Bearing (deg from north) of each matched polyline at the projection of its point."""
    out = np.empty(len(idx))
    for k, (i, p) in enumerate(zip(idx, pts)):
        ln = lines[i]
        s = ln.project(p)
        a, b = ln.interpolate(max(s - 15, 0)), ln.interpolate(min(s + 15, ln.length))
        out[k] = np.degrees(np.arctan2(b.x - a.x, b.y - a.y)) % 360
    return out


def main():
    camp = sys.argv[1]
    carto = gpd.read_file(A1 / "results/carto_a059fb0.geojson").to_crs(CRS)
    lines = carto.geometry.values
    frames = []
    for ch in pd.read_csv(ROOT / "article/data/raw_data_gps" / RAW[camp], sep=";", decimal=",",
                          encoding="utf-8-sig", chunksize=500_000):
        ch = ch[(ch.TIPO_POSIZIONE == 9) & (ch.STATO_MOTORE == 1) & (ch.SPEED >= 5)]
        g = gpd.GeoDataFrame(ch[["ID_VEICOLO", "DATA_REGISTRAZIONE", "SPEED", "HEADING"]],
                             geometry=gpd.points_from_xy(ch.LON, ch.LAT), crs=4326).to_crs(CRS)
        j = gpd.sjoin_nearest(g, carto[["poly_cid", "geometry"]], max_distance=MAXD, distance_col="d")
        j = j[~j.index.duplicated()]
        if not len(j):
            continue
        b = bearing_at(lines, j.index_right.values, j.geometry.values)
        diff = np.abs((j.HEADING.values - b + 180) % 360 - 180)
        ok = (diff <= MAXANG) | (diff >= 180 - MAXANG)
        j = j[ok]
        frames.append(pd.DataFrame({"poly_cid": j.poly_cid.values, "veh": j.ID_VEICOLO.values,
                                    "t": pd.to_datetime(j.DATA_REGISTRAZIONE.values, format="%d/%m/%Y %H:%M:%S"),
                                    "v": j.SPEED.values.astype(float)}))
        print(len(frames), sum(len(f) for f in frames), flush=True)
    m = pd.concat(frames, ignore_index=True)
    off = m[(m.t.dt.hour.between(10, 15)) & (m.t.dt.dayofweek < 5)]
    res = m.groupby("poly_cid").agg(n_points=("v", "size"), n_veh=("veh", "nunique"),
                                    v_median=("v", "median"), v_p85=("v", lambda s: s.quantile(.85)))
    res = res.join(off.groupby("poly_cid").v.agg(v_offpeak_median="median", n_offpeak="size"))
    out = A1 / "results/private" / f"gps_link_speeds_{camp}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    res.to_csv(out)
    print(out, len(res), "links;", int(res.n_points.sum()), "points")


if __name__ == "__main__":
    main()
