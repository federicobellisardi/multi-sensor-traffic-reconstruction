#!/usr/bin/env python3
"""Audit of where each detector sits on the model graph, from geometry only: simulated and observed volumes play no part in the flags.

Flags, fixed before their relation with the error was read (31 Oct):
  far: the detector coordinate is more than 50 m from its link.
  other_link_closer: another link of the graph is at least 30 m closer than its link, and within 30 m of the detector.
  road_differs: the OSM main road nearest the detector (within 30 m) has a ref, the link has a ref, and they differ.
  no_road: no link of the graph within 50 m.
  closed: the link is closed in the graph.
  province: the declared province differs from the province containing the coordinate (codes PA Parma, PI Piacenza, FO Forli-Cesena).
A detector is doubtful if any flag is set. Reported, not flags: link length and same-class parallel links within 200 m.

  python3 detector_placement.py -> model/results/demand/detector_placement.csv, detector_placement.json
"""
import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calibrate_demand as C  # noqa: E402
import demand_scaling as D  # noqa: E402
import detector_baselines as B  # noqa: E402
import od_matrix as M  # noqa: E402
import source_value as V  # noqa: E402
from paths import DATA_CACHE, RESULTS as R1, ROOT  # noqa: E402

CRS = 32632
CODE = {"Piacenza": "PI", "Parma": "PA", "Reggio nell'Emilia": "RE", "Modena": "MO", "Bologna": "BO", "Ferrara": "FE", "Ravenna": "RA", "Forlì-Cesena": "FO", "Rimini": "RI"}
FLAGS = ["far", "other_link_closer", "road_differs", "no_road", "closed", "province"]


def roads(g):
    """OSM main roads, Geofabrik extract nord-est-latest (downloaded 31 Oct 2026; ODbL)."""
    cache = DATA_CACHE / "osm/er_main_roads_latest.gpkg"
    if not cache.exists():
        box = tuple(g.to_crs(4326).total_bounds + np.array([-0.05, -0.05, 0.05, 0.05]))
        cl = ["motorway", "trunk", "primary", "secondary", "tertiary", "unclassified"]
        hw = "', '".join(cl + [c + "_link" for c in cl[:5]])
        o = pyogrio.read_dataframe(DATA_CACHE / "osm/nord-est-latest.osm.pbf", layer="lines", bbox=box, columns=["highway", "name", "other_tags"], where=f"highway IN ('{hw}')")
        o["ref"] = o.other_tags.fillna("").str.extract(r'"ref"=>"([^"]+)"', expand=False)
        o.to_crs(CRS)[["highway", "ref", "name", "geometry"]].to_file(cache, driver="GPKG")
    return gpd.read_file(cache)


def audit():
    bar = pd.read_csv(ROOT / "vars/extra/er_barriers.csv", sep=";").rename(columns={"ID": "coil"})
    car = pd.read_csv(ROOT / "vars/extra/er_barriers_cartodata.csv", sep=";").rename(columns={"tag": "coil"}).drop_duplicates("coil")
    d = bar.merge(car[["coil", "poly_lid"]], on="coil")
    d["poly_cid"] = LID2CID.reindex(d.poly_lid).values
    g = gpd.read_file(R1 / "carto_a059fb0.geojson").to_crs(CRS).set_index("poly_cid")
    rc = pd.read_csv(R1 / "road_class.csv").set_index("poly_cid")
    pts = gpd.GeoSeries(gpd.points_from_xy(d.Lon, d.Lat), crs=4326).to_crs(CRS)
    idx = g.sindex
    rows = []
    osm = roads(g)
    prov = gpd.read_file(ROOT / "vars/extra/er-shapes.geojson").to_crs(CRS)
    for r, p in zip(d.itertuples(), pts):
        own = g.geometry.get(r.poly_cid)
        near = g.iloc[idx.query(p.buffer(300), predicate="intersects")]
        dist = near.distance(p).sort_values()
        dl = float(own.distance(p)) if own is not None else np.nan
        close = dist.drop(r.poly_cid, errors="ignore")
        dn = float(close.iloc[0]) if len(close) else np.inf
        w = osm.iloc[osm.sindex.query(p.buffer(30), predicate="intersects")]
        w = w.assign(d=w.distance(p)).sort_values("d")
        wref = w.ref.iloc[0] if len(w) else None
        lref = rc.ref.get(r.poly_cid)
        refs = lambda x: {s.strip() for s in str(x).split(";")} if isinstance(x, str) and x else set()
        pa = prov[prov.contains(p)]
        par = 0
        if own is not None:
            cl = rc.road_class.get(r.poly_cid)
            around = g.iloc[idx.query(own.buffer(200), predicate="intersects")].drop(r.poly_cid, errors="ignore")
            for c, o in around.geometry.items():
                if rc.road_class.get(c) == cl and o.length > 500 and o.intersection(own.buffer(200)).length > 0.5 * min(own.length, o.length) and not o.touches(own):
                    par += 1
        rows.append(dict(coil=r.coil, poly_cid=r.poly_cid, prov=r.PRO, dist_link_m=dl, dist_other_link_m=dn, nearest_other_link=int(close.index[0]) if len(close) else -1,
                         road_class=rc.road_class.get(r.poly_cid), link_ref=lref, osm_ref=wref, osm_name=w.name.iloc[0] if len(w) else None, link_km=float(own.length / 1e3) if own is not None else np.nan, parallel_links=par,
                         far=dl > 50, other_link_closer=(dn < 30) and (dn + 30 <= dl), road_differs=bool(refs(wref) and refs(lref) and not refs(wref) & refs(lref)),
                         no_road=min(dl, dn) > 50, closed=bool(own is not None and g.oneway.get(r.poly_cid) == 3), province=bool(len(pa) and CODE.get(pa.PRO_NAME.iloc[0]) != r.PRO)))
    a = pd.DataFrame(rows)
    a["doubtful"] = a[FLAGS].any(axis=1)
    return a


def errors(a):
    t = D.group_observations()
    out = []
    for day in C.CAL_DAYS:
        q = t[t.day == day]
        s = V.daily(M.frozen_path(day), day, q.poly_lid)
        out.append(pd.Series(np.log10(np.clip(s, 1, None) / q.obs.values), index=q.coil.values, name=day))
    return pd.concat(out, axis=1).mean(axis=1).rename("log10_ratio")


LID2CID = pd.read_csv(next(M.frozen_path(C.CAL_DAYS[0]).glob("sim_*_uniq_*.csv")), sep=";", usecols=["poly_lid", "poly_cid"]).drop_duplicates().set_index("poly_lid").poly_cid


def main():
    a = audit().merge(errors(None), left_on="coil", right_index=True, how="left")
    a.to_csv(D.RES / "detector_placement.csv", index=False)
    v = a.dropna(subset=["log10_ratio"])
    res = {"detectors": int(len(a)), "evaluated": int(len(v)), "flags": {f: int(a[f].sum()) for f in FLAGS + ["doubtful"]},
           "dist_link_m_quantiles": [float(x) for x in a.dist_link_m.quantile([.5, .9, .99, 1])],
           "doubtful_vs_rest": {k: {"n": int(len(g)), "sd": float(g.log10_ratio.std()), "median_abs": float(g.log10_ratio.abs().median())} for k, g in v.groupby("doubtful")},
           "parallel_vs_rest": {str(k): {"n": int(len(g)), "sd": float(g.log10_ratio.std()), "median_abs": float(g.log10_ratio.abs().median())} for k, g in v.groupby(v.parallel_links > 0)}}
    (D.RES / "detector_placement.json").write_text(json.dumps(res, indent=1, default=str) + "\n")
    print(json.dumps(res, indent=1, default=str))
    print(a[a.doubtful][["coil", "prov", "dist_link_m", "dist_other_link_m", "link_ref", "osm_ref", "log10_ratio"] + FLAGS].round(2).to_string())
    print(v.assign(ab=v.log10_ratio.abs()).sort_values("ab", ascending=False).head(15)[["coil", "prov", "road_class", "dist_link_m", "link_ref", "osm_ref", "link_km", "parallel_links", "log10_ratio", "doubtful"]].round(2).to_string())


if __name__ == "__main__":
    main()
