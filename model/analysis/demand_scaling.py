#!/usr/bin/env python3
"""Systematic scaling of the mobile-phone demand with detector counts.

The OD tables cover only the operator's share of the travelling population. The historic
configuration generator rescaled individual OD pairs with detector counts of the simulated day; here
that rescaling is switched off and the whole demand is multiplied by one common factor k, the
inverse of the effective coverage.

k is chosen from joint simulations of 10 February 2020 with k = 1, 1.5, ..., 3 (step `scan`) on a
calibration half of the complete coils of that day (demand_scan_eval.py); the other half, the
other days of February 2020 and the June-July 2021 campaign are tests.

A per-class alternative (one factor per demand class, non-negative least squares on simulations of
each class alone, step `classes` + `fit`) was rejected: link volumes are not additive in the classes
(congestion and the trip-time budget of random-endpoint agents), and the fit removed the classes
with observed endpoints altogether. It is kept for the record (results/demand/demand_scaling.json).

Steps (run from the repository root):
  configs  : OD configurations without per-pair detector rescaling, all 24 hours, local clock
  classes  : one simulation per demand class for each day of the week (V6 route choice)
  fit      : per-class factors, leave-one-province-out assessment (rejected alternative)
  scan     : joint simulations of 10 Feb 2020 with a common factor k (list on the command line)
  final    : simulations with k from results/demand/k_choice.json (V6 route choice, and V0 for the
             routing comparison): one run per weekday, a determinism check, relabelled outputs for
             the other validation days

Cluster (IFISC nuredduna): `one NAME DAY` runs a single final simulation and `relabel` checks
determinism and relabels the other days (see hpc/). Locally, long runs must survive the
session: setsid nohup python3 ... < /dev/null &

Usage: python3 model/analysis/demand_scaling.py [configs|classes|fit|scan [k ...]|final]
"""
import contextlib
import io
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import nnls
sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import ROOT, RESULTS as R1, SIM_ENGINE, SIM_RUNS  # noqa: E402

HERE = Path(__file__).resolve().parent
RERUN = ROOT / "article/python/revision/rerun"
CONF = Path(os.environ.get("DEMAND_CONF", RERUN / "work/conf_clean"))  # mean OD of 13 Jan - 23 Feb 2020, see build_od_configs.py
RUNS = SIM_RUNS  # simulation outputs (outside the repository)
OUT = RUNS / "demand"
RES = R1 / "demand"
ENGINE = SIM_ENGINE
CHERRY_RADIUS_KM = float(os.environ.get("CHERRY_RADIUS_KM", 20.0))  # radius of the random trip ends and of the spread of the origins (radius_scan.py)
DEPARTURE_SHIFT_QUARTERS = int(os.environ.get("DEPARTURE_SHIFT_QUARTERS", 3))  # departures moved earlier, empirical (departure_shift_test.py)
SPREAD_ORIGIN = True  # origins of the located sources drawn around the point (population score, 10 km), not on one polyline
ROUTING = RUNS / "routing"
CLASSES = ["scr_dest", "scr_dest_prov", "src_rnd", "rnd_dest", "rnd_rnd"]
WEEK = [f"2020-02-{d}" for d in range(10, 17)]  # Monday to Sunday: the demand depends only on the weekday
DAYS = {2020: [f"2020-02-{d}" for d in range(10, 18)],
        2021: ["2021-06-28", "2021-06-29", "2021-06-30", "2021-07-01", "2021-07-02", "2021-07-03", "2021-07-04"]}
NPROC = 4
NO_CODE = bool(os.environ.get("NO_CODE"))  # demand without the destination code 000000000 (remove_od_code.py)


def tag(day):
    return day.replace("-", "")[2:]


def weekday_run(day):
    return WEEK[pd.Timestamp(day).dayofweek]


# ---------------------------------------------------------------- configurations
def configs():
    sys.path.insert(0, str(RERUN))
    import gen_configs as G
    from conf_2023 import conf
    CONF.mkdir(parents=True, exist_ok=True)
    for day in DAYS[2020] + DAYS[2021]:
        cw = conf({"wdir": str(CONF), "remove_local_output": False, "num_city": 50, "augmentation": False,
                   "coils_table_dir": str(G.WORK / "data"), "od_average_dir": str(G.WORK / "data"), "fixed_clock": True})
        with contextlib.redirect_stdout(io.StringIO()):
            c = cw.generate(f"{day} 00:00:00", f"{day} 23:45:00", day.replace("-", ""))
        json.dump(c, open(CONF / f"{day}.json", "w"))
    # same weekday -> same demand
    for day in DAYS[2020][7:] + DAYS[2021]:
        a = json.load(open(CONF / f"{day}.json"))["sources"]
        b = json.load(open(CONF / f"{weekday_run(day)}.json"))["sources"]
        assert {k: v["creation_rate"] for k, v in a.items()} == {k: v["creation_rate"] for k, v in b.items()}, day
    print("configurations written to", CONF)


def v6_config(day, variant="V6_gps_usage_classweights", sources=None, basename=None):
    """Configuration of `day` with the route choice of `variant` (as in routing_variants.run_one)."""
    sys.path.insert(0, str(HERE))
    import routing_variants as RV
    speeds, a_we, a_s = RV.VARIANTS[variant]
    if variant == "V6_gps_usage_classweights":
        a_s = float(os.environ.get("ALPHA_S", a_s))  # cost weight of travel time, re-run without the code
    c = json.load(open(CONF / f"{day}.json"))
    for k in ["file_barrier", "file_score_pop", "file_noturn"]:
        # generator paths point to the rebuilt workspace .../rerun/work/ws/covid_hep/vars/...: use the
        # project files (last "covid_hep/" component); missing files would silently disable barriers,
        # turn restrictions or the population score
        c[k] = str(ROOT / c[k].rsplit("covid_hep/", 1)[1])
        assert Path(c[k]).is_file(), c[k]
    # node scores for the random origins/destinations: ISTAT 2021 population (build_node_scores.py); the generator's
    # ace_score.csv has inf scores and node ids that do not match the network
    c["file_score_pop"] = str(ROOT / "vars/extra/node_score_pop2021.csv")
    assert Path(c["file_score_pop"]).is_file()
    c["file_pro"] = str(ROUTING / variant / "carto/er-speed.pro")
    c["file_pnt"] = str(ROUTING / variant / "carto/er-speed.pnt")
    if sources is not None:
        c["sources"] = sources
    for s in c["sources"].values():
        for p in s.get("pawns", {}).values():
            p["alpha_we"], p["alpha_speed"] = a_we, a_s
        s["creation_rate"] = np.roll(s["creation_rate"], -DEPARTURE_SHIFT_QUARTERS).tolist()
        if SPREAD_ORIGIN and "source_location" in s:
            s["spread_origin"] = True
    c["cherry_pick_mode"]["medium"] = CHERRY_RADIUS_KM
    c.update(enable_gui=False, dump_state_dt=-1)
    c.pop("file_cnt", None)
    if variant in RV.CLASS_WEIGHT_EXP:
        c["file_cnt"] = str(ROUTING / variant / "link_weights.cnt")
    c["state_basename"] = str(basename)
    return c


def run(cfg, basename):
    if NO_CODE and set(cfg["sources"]) == {"LOCALS"}:
        # runs with only the LOCALS source end with a segmentation fault under long output paths: short directory, linked
        short = RUNS.parent / f"nr_{RUNS.name.removeprefix('sim_runs_')}" / basename.parent.name  # the whole suffix: nocode2 and v2 must not share a directory
        short.mkdir(parents=True, exist_ok=True)
        basename.parent.parent.mkdir(parents=True, exist_ok=True)
        try:
            basename.parent.symlink_to(short)
        except FileExistsError:
            pass
        basename = short / basename.name
        cfg["state_basename"] = str(basename)
    basename.parent.mkdir(parents=True, exist_ok=True)
    f = basename.parent / f"{basename.name}.json"
    if list(basename.parent.glob(f"{basename.name}_uniq_*.csv")):
        return basename.name, 0, 0
    json.dump(cfg, open(f, "w"), indent=1)
    t0 = time.time()
    with open(basename.parent / f"{basename.name}.log", "w") as log:
        r = subprocess.run([str(ENGINE), str(f)], stdout=log, stderr=subprocess.STDOUT, cwd=basename.parent)
    rc = r.returncode
    if not rc and not list(basename.parent.glob(f"{basename.name}_uniq_*.csv")):
        rc = 1  # sim_engine catches its exceptions and exits with 0: a run without the link-flow file has failed
    return str(basename), rc, round(time.time() - t0)


def classes():
    jobs = []
    for day in sys.argv[2:] or WEEK:
        src = json.load(open(CONF / f"{day}.json"))["sources"]
        for cl in CLASSES:
            sel = {k: v for k, v in src.items() if cl in v["pawns"]}
            base = OUT / "classes" / cl / f"sim_{tag(day)}"
            jobs.append((v6_config(day, sources=sel, basename=base), base))
    with ThreadPoolExecutor(NPROC) as ex:
        for r in ex.map(lambda j: run(*j), jobs):
            print(*r, flush=True)


# ---------------------------------------------------------------- fit
def link_daily(path):
    d = pd.read_csv(path, sep=";")
    cols = [c for c in d if c.startswith("20")]
    return d.groupby("poly_lid")[cols].sum().sum(axis=1)


def observations():
    """Daily counts (both directions) of coils complete on each campaign day, local time."""
    sys.path.insert(0, str(HERE))
    import reconstruct_and_validate as P
    bar = pd.read_csv(ROOT / "vars/extra/er_barriers_cartodata.csv", sep=";")
    prov = pd.read_csv(ROOT / "vars/extra/er_barriers.csv", sep=";").set_index("ID").PRO
    rows = []
    for year, days in DAYS.items():
        obs = P.coil_table_local(year)
        for day in days:
            z = obs[obs.index.normalize() == pd.Timestamp(day)]
            for coil, lid in bar[["tag", "poly_lid"]].values:
                cc = [f"{coil}_0", f"{coil}_1"]
                if all(c in z for c in cc) and len(z) == 96 and z[cc].notna().all().all() and z[cc].sum().sum() > 0:
                    rows.append(dict(year=year, day=day, coil=int(coil), poly_lid=int(lid), prov=prov.get(coil, ""),
                                     obs=float(z[cc].sum().sum())))
    return pd.DataFrame(rows)


GROUPS = {"2020-02-10": (["2020-02-10", "2020-02-11", "2020-02-12", "2020-02-13", "2020-02-14", "2020-02-17"], 2),
          "2020-02-15": (["2020-02-15", "2020-02-16"], 1)}  # simulated day: (observed days, minimum valid days per interval)


def group_observations():
    """Mean daily counts (both directions) of the detectors over the weekday and weekend groups of February 2020.
    Each 15-min interval is the mean over its valid days; a detector enters a group if all 96 intervals of both
    directions have the minimum number of valid days. Column `day` is the simulated day compared with the group."""
    sys.path.insert(0, str(HERE))
    import reconstruct_and_validate as P
    bar = pd.read_csv(ROOT / "vars/extra/er_barriers_cartodata.csv", sep=";")
    prov = pd.read_csv(ROOT / "vars/extra/er_barriers.csv", sep=";").set_index("ID").PRO
    obs = P.coil_table_local(2020)
    rows = []
    for sim_day, (days, min_valid) in GROUPS.items():
        z = obs[np.isin(obs.index.strftime("%Y-%m-%d"), days)]
        assert len(z) == 96 * len(days), sim_day
        key = z.index.strftime("%H:%M")
        mean, valid = z.groupby(key).mean(), z.notna().groupby(key).sum()
        for coil, lid in bar[["tag", "poly_lid"]].values:
            cc = [f"{coil}_0", f"{coil}_1"]
            if all(c in z for c in cc) and (valid[cc] >= min_valid).all().all() and mean[cc].sum().sum() > 0:
                rows.append(dict(year=2020, day=sim_day, coil=int(coil), poly_lid=int(lid), prov=prov.get(coil, ""),
                                 obs=float(mean[cc].sum().sum())))
    return pd.DataFrame(rows)


def class_loads(o):
    for cl in CLASSES:
        loads = {d: link_daily(next((OUT / "classes" / cl).glob(f"sim_{tag(d)}_uniq_*.csv"))) for d in WEEK}
        o[cl] = [loads[weekday_run(d)].get(l, 0.0) for d, l in o[["day", "poly_lid"]].values]
    return o


def fit_factors(z, cols):
    w = 1 / np.sqrt(z.obs.values)
    k, _ = nnls(z[cols].values * w[:, None], z.obs.values * w)
    return k


def scores(obs, pred):
    lr = np.log10(np.clip(pred, 1, None) / obs)
    return dict(n=int(len(obs)), spearman=float(pd.Series(pred).corr(pd.Series(obs), method="spearman")),
                median_abs_log10=float(np.median(np.abs(lr))), within_factor2=float(np.mean(np.abs(lr) < np.log10(2))),
                volume_ratio=float(pred.sum() / obs.sum()))


def per_coil(z, pred):
    return z.assign(pred=pred).groupby("coil")[["obs", "pred"]].mean()


def fit():
    RES.mkdir(parents=True, exist_ok=True)
    o = class_loads(observations())
    o["unscaled"] = o[CLASSES].sum(axis=1)
    o.to_csv(RES / "coil_class_loads.csv", index=False)
    tr = o[o.year == 2020]
    models = {"unscaled": None, "global": ["unscaled"], "per_class": CLASSES}
    cv = {m: [] for m in models}
    for p in sorted(tr.prov.unique()):
        fit_set, test = tr[tr.prov != p], tr[tr.prov == p]
        for m, cols in models.items():
            pred = test.unscaled.values if cols is None else test[cols].values @ fit_factors(fit_set, cols)
            cv[m].append(per_coil(test, pred).assign(prov=p))
    report = {"cv_leave_one_province_out_2020": {m: scores(pd.concat(v).obs.values, pd.concat(v).pred.values) for m, v in cv.items()}}
    final = {m: (None if cols is None else fit_factors(tr, cols)) for m, cols in models.items()}
    report["factors"] = {"global": float(final["global"][0]), "per_class": dict(zip(CLASSES, map(float, final["per_class"])))}
    t21 = o[o.year == 2021]
    report["linear_prediction_2021"] = {m: scores(*(lambda c: (c.obs.values, c.pred.values))(per_coil(
        t21, t21.unscaled.values if cols is None else t21[cols].values @ final[m]))) for m, cols in models.items()}
    report["coils"] = {"2020": int(tr.coil.nunique()), "2021": int(t21.coil.nunique()), "provinces": sorted(tr.prov.unique())}
    pd.concat({m: pd.concat(v) for m, v in cv.items()}).to_csv(RES / "cv_leave_one_province_out.csv")
    (RES / "demand_scaling.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=1))


# ---------------------------------------------------------------- final simulations
def scaled_sources(day, k):
    src = json.load(open(CONF / f"{day}.json"))["sources"]
    for s in src.values():
        f = k[next(iter(s["pawns"]))]
        s["creation_rate"] = [int(round(f * v)) for v in s["creation_rate"]]
    return src


def relabel(src, dst, day):
    """Copy the outputs of simulation `src` to `dst` for `day`: same demand, only the date differs."""
    s0, s1 = pd.Timestamp(weekday_run(day)), pd.Timestamp(day)
    shift = int((s1 - s0).total_seconds())
    f = next(src.parent.glob(f"{src.name}_uniq_*.csv"))
    head, rest = open(f).read().split("\n", 1)
    (dst.parent / f"{dst.name}_uniq_{tag(day)}_000000.csv").write_text(head.replace(f"{s0:%Y-%m-%d}", f"{s1:%Y-%m-%d}") + "\n" + rest)
    lines = open(next(src.parent.glob(f"{src.name}_barriers_*.csv"))).read().splitlines()
    out = [lines[0]]
    for line in lines[1:]:
        dt, _, other = line.split(";", 2)
        t = pd.Timestamp(dt) + pd.Timedelta(seconds=shift)  # local wall-clock time
        out.append(f"{t:%Y-%m-%d %H:%M:%S};{int(t.tz_localize('Europe/Rome').timestamp())};{other}")
    (dst.parent / f"{dst.name}_barriers_{tag(day)}_000000.csv").write_text("\n".join(out) + "\n")


def final():
    """Simulations of the validation days with k from k_choice.json. The demand depends only on the
    weekday and the simulator is deterministic, so each weekday is simulated once (plus 17 Feb 2020 as
    a check) and the outputs are relabelled for the other days with the same weekday."""
    with ThreadPoolExecutor(NPROC) as ex:
        for r in ex.map(lambda j: one(*j), final_jobs()):
            print(*r, flush=True)
    relabel_all()


VARIANTS = {"V6_scaled": "V6_gps_usage_classweights", "V0_scaled": "V0_default_distance"}


def final_jobs():
    return [(name, day) for name in VARIANTS for day in WEEK + (["2020-02-17"] if name == "V6_scaled" else [])]


def k_of(day):
    """k of the day type: weekdays k, Saturdays and Sundays k_weekend."""
    c = json.load(open(RES / "k_choice.json"))
    return c["k_weekend"] if pd.Timestamp(day).dayofweek >= 5 else c["k"]


def province_scaled(src):
    """Province factors adopted on 31 Oct (province_demand.py): each located source times the geometric mean of the factors of its ends in the region."""
    import geopandas as gpd
    code = {"Piacenza": "PI", "Parma": "PA", "Reggio nell'Emilia": "RE", "Modena": "MO", "Bologna": "BO", "Ferrara": "FE", "Ravenna": "RA", "Forlì-Cesena": "FO", "Rimini": "RI"}
    shapes = gpd.read_file(ROOT / "vars/extra/er-shapes.geojson").to_crs(4326)
    def prov(loc):
        h = shapes[shapes.contains(gpd.points_from_xy([loc["lon"]], [loc["lat"]])[0])]
        return code.get(h.PRO_NAME.iloc[0]) if len(h) else None
    if not (RES / "province_factors.json").exists():
        return src  # factors not adopted
    f = json.load(open(RES / "province_factors.json"))
    for s in src.values():
        ends = [f[p] for p in (prov(s[e]) for e in ("source_location", "dest_location") if e in s) if p]
        if ends:
            g = float(np.prod(ends)) ** (1 / len(ends))
            s["creation_rate"] = [int(round(g * v)) for v in s["creation_rate"]]
    return src


def one(name, day):
    """One final simulation (cluster job): python3 demand_scaling.py one V6_scaled 2020-02-10"""
    f = k_of(day)
    base = OUT / name / f"sim_{tag(day)}"
    return run(v6_config(day, VARIANTS[name], province_scaled(scaled_sources(day, {c: f for c in CLASSES})), base), base)


def relabel_all():
    f = json.load(open(RES / "k_choice.json"))["k"]
    k = {c: f for c in CLASSES}
    variants = [(v, n) for n, v in VARIANTS.items()]
    # determinism check: 10 Feb relabelled to 17 Feb must equal the simulated 17 Feb
    chk = OUT / "V6_scaled" / "check" / "sim_200217"
    chk.parent.mkdir(exist_ok=True)
    relabel(OUT / "V6_scaled" / "sim_200210", chk, "2020-02-17")
    for kind in ("uniq", "barriers"):
        a = next((OUT / "V6_scaled").glob(f"sim_200217_{kind}_*.csv")).read_bytes()
        b = next(chk.parent.glob(f"sim_200217_{kind}_*.csv")).read_bytes()
        assert a == b, f"simulation not reproducible across identical weekdays ({kind})"
    print("determinism check passed: 2020-02-17 == 2020-02-10 relabelled", flush=True)
    for variant, name in variants:
        for day in DAYS[2020] + DAYS[2021]:
            dst = OUT / name / f"sim_{tag(day)}"
            if day in WEEK or list(dst.parent.glob(f"{dst.name}_uniq_*.csv")):
                continue
            relabel(OUT / name / f"sim_{tag(weekday_run(day))}", dst, day)
            cfg = v6_config(day, variant, scaled_sources(day, k), dst)
            cfg["relabelled_from"] = weekday_run(day)
            json.dump(cfg, open(dst.parent / f"{dst.name}.json", "w"), indent=1)
            print("relabelled", dst, "from", weekday_run(day), flush=True)


SCAN = [1.0, 1.3, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0, 2.2, 2.5, 3.0]


def scan():
    """Joint simulations of 10 February 2020 with all demand scaled by a common factor
    (factors from the command line, default SCAN)."""
    jobs = []
    for f in [float(x) for x in sys.argv[2:]] or SCAN:
        base = OUT / "scan" / f"k{f:.1f}" / "sim_200210"
        jobs.append((v6_config("2020-02-10", sources=scaled_sources("2020-02-10", {c: f for c in CLASSES}), basename=base), base))
    with ThreadPoolExecutor(NPROC) as ex:
        for r in ex.map(lambda j: run(*j), jobs):
            print(*r, flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "one":
        res = one(sys.argv[2], sys.argv[3])
        print(*res, flush=True)
        sys.exit(1 if res[1] else 0)  # a failed simulation must fail the batch job
    else:
        {"configs": configs, "classes": classes, "fit": fit, "scan": scan, "final": final,
         "relabel": relabel_all}[sys.argv[1]]()
