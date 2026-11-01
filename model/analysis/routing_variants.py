#!/usr/bin/env python3
"""Route-choice calibration with GPS link speeds by road class.

1. class speeds: median off-peak GPS speed (private vehicles, Forli-Cesena, Feb 2020) of the
   matched links of each OSM road class (links with >= 50 matched points), from
   results/private/gps_link_speeds_202002.csv and results/road_class.csv;
2. a copy of the project cartography (vars/carto/er-speed.pro, commit a059fb0) in which only the
   speed column is replaced by the class speed (topology, lengths, one-way flags unchanged);
3. minimocas runs of one calibration day for each variant (link cost = length * (a_we + a_s *
   v_min / v), a_we + a_s = 1);
4. metrics: Spearman correlation between simulated daily link volumes and
   (i) GPS link counts in Forli-Cesena (calibration), (ii) daily volumes of MTS detectors outside
   the province of Forli-Cesena (validation).

Usage: python3 model/analysis/routing_variants.py prepare|run|evaluate [day]
"""
import json
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import ROOT, RESULTS as R1, SIM_ENGINE, SIM_RUNS  # noqa: E402

OUT = SIM_RUNS / "routing"
RES = R1 / "routing"
CONF = ROOT / "article/python/revision/rerun/work/conf_fixed"
ENGINE = SIM_ENGINE  # patched add_bpmatrix (identical output on baseline)
VARIANTS = {"V0_default_distance": ("default", 1.0, 0.0), "V1_gps_distance": ("gps", 1.0, 0.0),
            "V2_gps_time": ("gps", 0.0, 1.0), "V3_gps_mixed": ("gps", 0.5, 0.5),
            "V4_gps_time_classweights": ("gps", 0.0, 1.0), "V5_gps_time_classweights_sqrt": ("gps", 0.0, 1.0),
            "V6_gps_usage_classweights": ("gps", 0.5, 0.0)}  # cost = length*(0.5 + 0.5*low-usage penalty from file_cnt)
# transition weights of the random-walk agents (minimocas file_cnt): exponent applied to the
# median daily GPS count per link of each road class (Forli-Cesena, Feb 2020)
CLASS_WEIGHT_EXP = {"V4_gps_time_classweights": 1.0, "V5_gps_time_classweights_sqrt": 0.5, "V6_gps_usage_classweights": 1.0}
PRO_COLS = ["poly_cid", "nF", "nT", "length", "lvl_ps", "a", "b", "c", "speed", "oneway", "name"]


def class_speeds():
    sp = pd.read_csv(R1 / "private/gps_link_speeds_202002.csv")
    rc = pd.read_csv(R1 / "road_class.csv")
    d = sp.merge(rc, on="poly_cid")
    d = d[(d.n_points >= 50) & d.v_offpeak_median.notna() & (d.road_class != "unmatched")]
    t = d.groupby("road_class").agg(links=("poly_cid", "size"), v_kmh=("v_offpeak_median", "median"),
                                    v_kmh_iqr_low=("v_offpeak_median", lambda s: s.quantile(.25)),
                                    v_kmh_iqr_high=("v_offpeak_median", lambda s: s.quantile(.75)))
    return t


def class_gps_weights():
    """Median daily GPS count per link (both directions) of each OSM road class, Feb 2020."""
    keep = set(pd.read_csv(R1 / "private/gps_links_unchanged.csv", index_col=0).query("hausdorff_m <= 1").index)
    v = pd.read_csv(ROOT / "work_viasat/viasat_20200210_20200218_timed_fluxes.csv", sep=";", parse_dates=["time"])
    v = v[v.cid.isin(keep)]
    days = v.time.dt.date.nunique()
    g = v.groupby("cid").total_fluxes.sum() / days
    g = g[g > 0]  # links inside the probe coverage (Forli-Cesena)
    rc = pd.read_csv(R1 / "road_class.csv").set_index("poly_cid").road_class
    t = g.groupby(rc.reindex(g.index)).agg(["size", "median"])
    t.columns = ["links", "median_daily_gps"]
    return t


def prepare():
    RES.mkdir(parents=True, exist_ok=True)
    w = class_gps_weights()
    w.to_csv(RES / "class_gps_weights.csv")
    print(w)
    rcl = pd.read_csv(R1 / "road_class.csv").set_index("poly_cid").road_class
    pro = pd.read_csv(ROOT / "vars/carto/er-speed.pro", sep=r"\s+", header=None, skiprows=1, usecols=[0], names=["cid"])
    base = w.median_daily_gps.drop("unmatched", errors="ignore")
    for v, e in CLASS_WEIGHT_EXP.items():
        ww = (base / base.min()) ** e
        rows = ["lid cid cntFT cntTF"]
        for lid, cid in enumerate(pro.cid):
            k = max(1, int(round(10 * ww.get(rcl.get(cid, "unclassified"), 1.0))))
            rows.append(f"{lid} {cid} {k} {k}")
        (OUT / v).mkdir(parents=True, exist_ok=True)
        (OUT / v / "link_weights.cnt").write_text("\n".join(rows) + "\n")
    t = class_speeds()
    t.to_csv(RES / "class_speeds.csv")
    print(t)
    rc = pd.read_csv(R1 / "road_class.csv").set_index("poly_cid").road_class
    lines = open(ROOT / "vars/carto/er-speed.pro").read().splitlines()
    head, body = lines[0], lines[1:]
    fallback = t.v_kmh.get("unclassified", t.v_kmh.min())
    new = [head]
    for ln in body:
        tok = ln.split()
        cls = rc.get(int(tok[0]), "unmatched")
        tok[8] = f"{t.v_kmh.get(cls, fallback):.1f}"  # minimocas reads km/h (carto.cpp: speed * kmh_to_ms)
        new.append(" ".join(tok))
    for v, (speeds, *_rest) in VARIANTS.items():
        d = OUT / v / "carto"
        d.mkdir(parents=True, exist_ok=True)
        src = ROOT / "vars/carto"
        if speeds == "gps":
            (d / "er-speed.pro").write_text("\n".join(new) + "\n")
        else:
            shutil.copy(src / "er-speed.pro", d / "er-speed.pro")
        shutil.copy(src / "er-speed.pnt", d / "er-speed.pnt")


def run_one(variant, day):
    speeds, a_we, a_s = VARIANTS[variant]
    c = json.load(open(CONF / f"{day}.json"))
    for k in ["file_barrier", "file_score_pop", "file_noturn"]:
        c[k] = str(ROOT / c[k].split("covid_hep/")[1])
    c["file_pro"] = str(OUT / variant / "carto/er-speed.pro")
    c["file_pnt"] = str(OUT / variant / "carto/er-speed.pnt")
    for s in c["sources"].values():
        for p in s.get("pawns", {}).values():
            p["alpha_we"], p["alpha_speed"] = a_we, a_s
    c.update(enable_gui=False, dump_state_dt=-1)
    if variant in CLASS_WEIGHT_EXP:
        c["file_cnt"] = str(OUT / variant / "link_weights.cnt")
    tag = day.replace("-", "")[2:]
    c["state_basename"] = str(OUT / variant / f"sim_{tag}")
    cfg = OUT / variant / f"sim_{tag}.json"
    json.dump(c, open(cfg, "w"), indent=1)
    t0 = time.time()
    with open(OUT / variant / f"sim_{tag}.log", "w") as log:
        r = subprocess.run([str(ENGINE), str(cfg)], stdout=log, stderr=subprocess.STDOUT, cwd=OUT / variant)
    return variant, day, r.returncode, round(time.time() - t0)


def daily(variant, day):
    tag = day.replace("-", "")[2:]
    f = OUT / variant / f"sim_{tag}_uniq_{tag}_000000.csv"
    d = pd.read_csv(f, sep=";")
    cols = [c for c in d if c.startswith("20")]
    return d.groupby("poly_cid")[cols].sum().sum(axis=1), d.groupby("poly_lid")[cols].sum().sum(axis=1)


def evaluate(day):
    keep = set(pd.read_csv(R1 / "private/gps_links_unchanged.csv", index_col=0).query("hausdorff_m <= 1").index)
    v = pd.read_csv(ROOT / "work_viasat/viasat_20200210_20200218_timed_fluxes.csv", sep=";", parse_dates=["time"])
    v = v[(v.time.dt.date == pd.Timestamp(day).date()) & v.cid.isin(keep)]
    gps = v.groupby("cid").total_fluxes.sum()
    gps = gps[gps > 0]
    bar = pd.read_csv(ROOT / "vars/extra/er_barriers_cartodata.csv", sep=";")
    reg = pd.read_csv(ROOT / "vars/extra/er_barriers.csv", sep=";").set_index("ID").PRO
    obs = pd.read_csv(ROOT / "data/old_coils_data/_coils_table_200201-000000_200331-234500.csv", sep=";", index_col=0)
    obs.index = pd.to_datetime(obs.index, utc=True).tz_convert("Europe/Rome").tz_localize(None)
    obs = obs[obs.index.normalize() == pd.Timestamp(day)]
    rc = pd.read_csv(R1 / "road_class.csv").set_index("poly_cid").road_class
    rows = []
    for variant in VARIANTS:
        try:
            by_cid, by_lid = daily(variant, day)
        except (FileNotFoundError, IndexError):
            continue
        g = gps.index.intersection(by_cid.index)
        coil = []
        for tag, lid in bar[["tag", "poly_lid"]].values:
            cc = [f"{tag}_0", f"{tag}_1"]
            if all(c in obs for c in cc) and len(obs) == 96 and obs[cc].notna().all().all():
                coil.append((tag, reg.get(tag, ""), obs[cc].sum().sum(), by_lid.get(lid, 0)))
        coil = pd.DataFrame(coil, columns=["tag", "prov", "obs", "sim"])
        out = coil[coil.prov != "FO"]
        lr = np.log10(out.sim.clip(lower=1) / out.obs)
        share_main = by_cid[rc.reindex(by_cid.index).isin(["motorway", "trunk", "primary"])].sum() / by_cid.sum()
        rows.append(dict(variant=variant, day=day,
                         calib_gps_links=len(g), calib_spearman_gps=by_cid[g].corr(gps[g], method="spearman"),
                         valid_coils_outside_FC=len(out), valid_spearman_coils=out.sim.corr(out.obs, method="spearman"),
                         valid_median_log10_ratio=lr.median(), valid_share_within_factor2=(lr.abs() < np.log10(2)).mean(),
                         all_coils_spearman=coil.sim.corr(coil.obs, method="spearman"),
                         share_volume_main_roads=share_main))
    r = pd.DataFrame(rows)
    RES.mkdir(parents=True, exist_ok=True)
    r.to_csv(RES / f"routing_variants_{day}.csv", index=False)
    print(r.round(3).to_string())


def main():
    step = sys.argv[1]
    day = sys.argv[2] if len(sys.argv) > 2 else "2020-02-10"
    if step == "prepare":
        prepare()
    elif step == "run":
        with ThreadPoolExecutor(4) as ex:
            todo = sys.argv[3].split(",") if len(sys.argv) > 3 else [v for v in VARIANTS if v != "V0_default_distance"]
            for res in ex.map(lambda v: run_one(v, day), todo):
                print(*res, flush=True)
    elif step == "evaluate":
        evaluate(day)


if __name__ == "__main__":
    main()
