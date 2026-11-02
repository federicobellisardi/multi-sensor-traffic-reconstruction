#!/usr/bin/env python3
"""What explains the error of the final model at single roads. Diagnostic, selects nothing (results/experiments/PROTOCOL_DIAGNOSTICS.md).

  python3 road_error_diagnosis.py -> model/results/experiments/road_error_diagnosis.json, model/results/private/road_error_features.csv
"""
import json
import sys
from pathlib import Path

import geopandas as gpd
import networkx as nx
import numpy as np
import pandas as pd
import pyogrio
from scipy.stats import spearmanr
from shapely.geometry import LineString
from sklearn.ensemble import RandomForestRegressor

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calibrate_demand as C  # noqa: E402
import demand_scaling as D  # noqa: E402
import source_value as V  # noqa: E402
from paths import DATA_CACHE, ROOT, RESULTS as R1  # noqa: E402

MON, SAT = C.CAL_DAYS
CRS, SEED = 32632, 20261101
PBF = DATA_CACHE / "osm/nord-est-latest.osm.pbf"
MAIN = ["motorway", "trunk", "primary", "secondary", "tertiary"]
MINOR = ["unclassified", "residential"]
SECTIONS = ROOT / "data/istat_2021/SHP/R08_21_WGS84.shp"
GROUPS = {"class": None, "province": None, "network": ["log_length", "log_betweenness"], "parallel": ["log_parallel_n", "log_parallel_len"],
          "omitted": ["log_omit_main", "log_omit_minor", "log_omit_parallel"], "activity": ["log_pop_1", "log_pop_5", "log_poi_1", "log_poi_5"], "boundary": ["log_boundary"]}
N_REP, N_PERM = 100, 999


def bearing(line):
    a, b = np.array(line.coords[0]), np.array(line.coords[-1])
    return np.degrees(np.arctan2(b[1] - a[1], b[0] - a[0])) % 180


def close(a, b, tol=30):
    d = abs(a - b) % 180
    return min(d, 180 - d) <= tol


def osm_lines(bbox):
    cache = R1 / "private/osm_lines_diagnosis.gpkg"
    if cache.exists():
        return gpd.read_file(cache)
    hw = "', '".join(MAIN + MINOR + [c + "_link" for c in MAIN])
    o = pyogrio.read_dataframe(PBF, layer="lines", bbox=bbox, columns=["highway"], where=f"highway IN ('{hw}')").to_crs(CRS)
    o["group"] = np.where(o.highway.str.replace("_link", "", regex=False).isin(MAIN), "main", "minor")
    o = o[["group", "geometry"]]
    o.to_file(cache, driver="GPKG")
    return o


def features(t):
    carto = gpd.read_file(R1 / "carto_a059fb0.geojson").to_crs(CRS)
    lid = pd.read_csv(ROOT / "vars/carto/er-speed.pro", sep=r"\s+", header=None, skiprows=1, usecols=[0], names=["cid"]).cid
    carto = carto.set_index("poly_cid").loc[lid.values].reset_index()  # row number is poly_lid
    cls = pd.read_csv(R1 / "road_class.csv").set_index("poly_cid").road_class
    bar = pd.read_csv(ROOT / "vars/extra/er_barriers_cartodata.csv", sep=";").drop_duplicates("tag").set_index("tag")
    u = t.drop_duplicates("coil")[["coil", "poly_lid", "prov"]].reset_index(drop=True)
    pts = gpd.GeoDataFrame(u, geometry=gpd.points_from_xy(bar.lon.reindex(u.coil), bar.lat.reindex(u.coil)), crs=4326).to_crs(CRS)
    g = nx.Graph()
    for i, r in carto.iterrows():
        if not g.has_edge(r.nF, r.nT) or g[r.nF][r.nT]["length"] > r.length:
            g.add_edge(r.nF, r.nT, length=r.length, lid=i)
    eb = nx.edge_betweenness_centrality(g, k=1000, weight="length", seed=SEED)
    ebl = {g[a][b]["lid"]: v for (a, b), v in eb.items()}
    bbox = tuple(gpd.GeoSeries(carto.geometry, crs=CRS).to_crs(4326).total_bounds + np.array([-.05, -.05, .05, .05]))
    print("osm lines", flush=True)
    osm = osm_lines(bbox)
    print(len(osm), "ways", flush=True)
    poi = pyogrio.read_dataframe(PBF, layer="points", bbox=bbox, columns=["other_tags"],
                                 where="other_tags LIKE '%\"shop\"=>%' OR other_tags LIKE '%\"amenity\"=>%' OR other_tags LIKE '%\"office\"=>%'").to_crs(CRS)
    sec = gpd.read_file(SECTIONS)[["POP21", "geometry"]].to_crs(CRS)
    sec["geometry"] = sec.geometry.representative_point()
    region = gpd.read_file(ROOT / "vars/extra/er-shapes.geojson").to_crs(CRS).union_all()
    bear = carto.geometry.map(bearing)
    rows = []
    print("features", flush=True)
    for _, p in pts.iterrows():
        link = carto.loc[p.poly_lid]
        b1, b5 = p.geometry.buffer(1000), p.geometry.buffer(5000)
        cand = carto.iloc[carto.sindex.query(b1)]
        par = cand[[not ({c.nF, c.nT} & {link.nF, link.nT}) and close(bear[i], bear[p.poly_lid]) for i, c in cand.iterrows()]]
        # the part of each way not within 30 m of a model link is what the model network omits
        near = carto.iloc[carto.sindex.query(b1.buffer(30))].geometry.buffer(30).union_all()
        o = osm.iloc[osm.sindex.query(b1)].copy()
        o["geometry"] = o.geometry.intersection(b1).difference(near)
        o = o[~o.geometry.is_empty].explode(ignore_index=True)
        same = np.array([close(bearing(LineString([x.coords[0], x.coords[-1]])), bear[p.poly_lid]) if x.length > 0 else False for x in o.geometry], dtype=bool)
        L = o.geometry.length
        rows.append(dict(coil=p.coil, road_class=cls.get(link.poly_cid, "unclassified"), log_length=np.log10(link.length), log_betweenness=np.log10(ebl.get(p.poly_lid, 0) + 1e-5),
                         log_parallel_n=np.log1p(len(par)), log_parallel_len=np.log1p(par.geometry.intersection(b1).length.sum()),
                         log_omit_main=np.log1p(L[o.group == "main"].sum()), log_omit_minor=np.log1p(L[o.group == "minor"].sum()), log_omit_parallel=np.log1p(L[same].sum()),
                         log_pop_1=np.log1p(sec.iloc[sec.sindex.query(b1, predicate="contains")].POP21.sum()), log_pop_5=np.log1p(sec.iloc[sec.sindex.query(b5, predicate="contains")].POP21.sum()),
                         log_poi_1=np.log1p(len(poi.sindex.query(b1, predicate="contains"))), log_poi_5=np.log1p(len(poi.sindex.query(b5, predicate="contains"))),
                         log_boundary=np.log1p(region.boundary.distance(p.geometry))))
    return u.merge(pd.DataFrame(rows), on="coil")


def design(f, name):
    if name == "class":
        return pd.get_dummies(f.road_class, drop_first=True).astype(float).values
    if name == "province":
        return pd.get_dummies(f.prov, drop_first=True).astype(float).values
    x = f[GROUPS[name]].values.astype(float)
    return (x - x.mean(0)) / x.std(0)


def cv_r2(x, y, folds):
    """Out-of-fold R2, each fold compared with the training mean; folds is (repeats, n) of fold labels."""
    x = np.column_stack([np.ones(len(y)), x])
    out = []
    for lab in folds:
        pred, base = np.empty(len(y)), np.empty(len(y))
        for k in np.unique(lab):
            te = lab == k
            b = np.linalg.lstsq(x[~te], y[~te], rcond=None)[0]
            pred[te], base[te] = x[te] @ b, y[~te].mean()
        out.append(1 - ((y - pred) ** 2).sum() / ((y - base) ** 2).sum())
    return float(np.mean(out))


def holm(p):
    k = list(p)
    o = np.argsort([p[i] for i in k])
    adj, run = {}, 0.0
    for r, i in enumerate(o):
        run = max(run, min(1.0, (len(k) - r) * p[k[i]]))
        adj[k[i]] = run
    return adj


def analyse(f, y, rng):
    n = len(y)
    fold = lambda m: np.array([rng.permutation(np.arange(n) % 5) for _ in range(m)])
    folds = fold(N_REP)
    xs = {g: design(f, g) for g in GROUPS}
    full = np.column_stack(list(xs.values()))
    res = {"n": n, "sd": float(y.std()), "r2_full": cv_r2(full, y, folds)}
    prov = f.prov.values
    res["r2_leave_province_out"] = cv_r2(full, y, pd.factorize(prov)[0][None, :])
    rf = RandomForestRegressor(n_estimators=500, min_samples_leaf=3, oob_score=True, random_state=SEED, n_jobs=4).fit(full, y)
    res["r2_forest_oob"] = float(rf.oob_score_)
    small = fold(5)
    pv, gr = {}, {}
    for g in GROUPS:
        without = np.column_stack([xs[h] for h in GROUPS if h != g])
        gain = res["r2_full"] - cv_r2(without, y, folds)
        ref = cv_r2(full, y, small) - cv_r2(without, y, small)
        null = [cv_r2(np.column_stack([without, xs[g][rng.permutation(n)]]), y, small[:1]) - cv_r2(without, y, small[:1]) for _ in range(N_PERM)]
        pv[g] = float((1 + np.sum(np.array(null) >= ref)) / (N_PERM + 1))
        gr[g] = {"alone": cv_r2(xs[g], y, folds), "lost_if_removed": float(gain), "p": pv[g]}
    for g, a in holm(pv).items():
        gr[g]["p_holm"] = a
    res["groups"] = gr
    return res


def main():
    rng = np.random.default_rng(SEED)
    t = D.group_observations()
    cache = R1 / "private/road_error_features.csv"
    f = pd.read_csv(cache) if cache.exists() else features(t)
    f.to_csv(cache, index=False)
    ys = {}
    for name, day in (("monday", MON), ("saturday", SAT)):
        q = t[t.day == day]
        s = V.daily(D.OUT / "V6_scaled", day, q.poly_lid)
        ys[name] = pd.Series(np.log10(s / q.obs.values), index=q.coil.values)[s > 0]
    l = pd.read_csv(R1 / "corrected/loo_detectors.csv").dropna(subset=["raw_total"])
    l = l[l.day.str.startswith("2021")].groupby(["coil", "day"])[["obs_total", "raw_total"]].sum().groupby("coil").mean()
    ys["2021"] = np.log10(l.raw_total[l.raw_total > 0] / l.obs_total[l.raw_total > 0])
    res = {"seed": SEED, "persistence_monday_2021": float(pd.concat([ys["monday"], ys["2021"]], axis=1).dropna().corr().iloc[0, 1])}
    num = [c for g in GROUPS.values() if g for c in g]
    for name, y in ys.items():
        print(name, flush=True)
        z = f[f.coil.isin(y.index)].reset_index(drop=True)
        v = y.reindex(z.coil).values
        res[name] = {"signed": analyse(z, v, rng), "absolute": analyse(z, np.abs(v), rng),
                     "spearman": {c: [float(spearmanr(z[c], v)[0]), float(spearmanr(z[c], np.abs(v))[0])] for c in num},
                     "by_class": {k: {"n": int(len(w)), "median": float(np.median(w)), "median_abs": float(np.median(np.abs(w)))} for k, w in pd.Series(v).groupby(z.road_class.values)}}
    (R1 / "experiments/road_error_diagnosis.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res)[:400])


if __name__ == "__main__":
    main()
