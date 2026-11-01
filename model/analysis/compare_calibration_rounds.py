#!/usr/bin/env python3
"""Effect of an engine change on the raw simulated volumes at the calibration detectors.

Compares the current calibration runs ($SIM_RUNS/calibration) with an archived round, each at its own k.
Only the calibration half of the detectors is used (group means, calibrate_demand.load).
Rule fixed before the runs: the change is supported only if the 95% paired bootstrap interval over detectors of the
difference of the sd of log10(sim/obs), new - reference, is entirely below zero.

  python3 compare_calibration_rounds.py REFERENCE_DIR K_NEW K_REF
      -> model/results/demand/calibration_round_comparison.json, calibration_round_comparison.{pdf,svg,png}
"""
import json
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calibrate_demand as C  # noqa: E402
import demand_scaling as D  # noqa: E402
from paths import ROOT  # noqa: E402

N_BOOT, SEED = 2000, 20261036
DAY = "2020-02-10"
BINS = [0, 2, 5, 10, 20, 1000]
NEW, REF = "#0072B2", "#D55E00"


def sd_log(sim, obs):
    m = sim > 0
    return float(np.log10(sim[m] / obs[m]).std())


def per_coil(o, sim):
    return pd.DataFrame({"coil": o.coil.values, "obs": o.obs.values, "sim": sim}).groupby("coil").mean()


def metrics(o, sim):
    obs = o.obs.values
    m = sim > 0
    lr = np.log10(sim[m] / obs[m])
    a = per_coil(o, sim)
    return {"sd_log10": sd_log(sim, obs), "mean_sq_log10": float((lr ** 2).mean()), "median_abs_log10": float(np.median(np.abs(lr))),
            "spearman": float(spearmanr(a.obs, a.sim)[0]), "slope": float(np.polyfit(np.log10(a.obs), np.log10(a.sim.clip(lower=1)), 1)[0]),
            "volume_ratio": float(sim.sum() / obs.sum()), "within_factor2": float(np.mean(np.abs(lr) < np.log10(2)))}


def alive_23h(base, name):
    d = pd.read_csv(next((base / name).glob(f"sim_{D.tag(DAY)}_pawn_*.csv")), sep=";", usecols=["timestamp"])
    return int((d.timestamp == d.timestamp.max()).sum())


def municipal_distance(base, name, coils):
    """Distance (km) from each detector to the nearest located municipal source point."""
    cfg = json.load(open(base / name / f"sim_{D.tag(DAY)}.json"))
    pts = [(v.get("source_location") or v.get("dest_location")) for v in cfg["sources"].values()
           if next(iter(v["pawns"])) in ("src_rnd", "rnd_dest")]
    pts = pd.DataFrame([p for p in pts if p]).drop_duplicates()
    g = gpd.GeoSeries(gpd.points_from_xy(pts.lon, pts.lat), crs=4326).to_crs(32632)
    bar = pd.read_csv(ROOT / "vars/extra/er_barriers_cartodata.csv", sep=";").drop_duplicates("tag").set_index("tag").loc[coils]
    c = gpd.GeoSeries(gpd.points_from_xy(bar.lon, bar.lat), crs=4326).to_crs(32632)
    return pd.Series([g.distance(p).min() / 1e3 for p in c], index=coils)


def road_class(base, name, o):
    u = pd.read_csv(next((base / name).glob(f"sim_{D.tag(DAY)}_uniq_*.csv")), sep=";", usecols=["poly_lid", "poly_cid"]).drop_duplicates("poly_lid")
    rc = pd.read_csv(ROOT / "model/results/road_class.csv").set_index("poly_cid").road_class
    return o.drop_duplicates("coil").set_index("coil").poly_lid.map(u.set_index("poly_lid").poly_cid).map(rc)


def diagnosis(o, sim, dist, rc):
    a = per_coil(o, sim)
    lr = np.log10(a.sim.clip(lower=1) / a.obs)
    prov = o.drop_duplicates("coil").set_index("coil").prov
    summary = lambda g: {str(k): {"n": int(len(v)), "median_log10_ratio": float(v.median())} for k, v in g}
    return {"by_road_class": summary(lr.groupby(rc.reindex(lr.index).values)),
            "by_province": summary(lr.groupby(prov.reindex(lr.index).values)),
            "by_distance_km": summary(lr.groupby(pd.cut(dist.reindex(lr.index), BINS).astype(str).values)),
            "spearman_ratio_vs_distance": float(spearmanr(dist.reindex(lr.index), lr)[0])}, lr


def figure(o, new, ref, dist, labels, path):
    plt.rcParams.update({"font.size": 7.5, "font.family": "sans-serif", "axes.linewidth": .6, "axes.spines.top": False,
                         "axes.spines.right": False, "pdf.fonttype": 42, "svg.fonttype": "none"})
    fig, ax = plt.subplots(1, 3, figsize=(7.2, 2.6), constrained_layout=True)
    lim = (3e2, 3e5)
    for a, sim, col, mk, lab, t in ((ax[0], ref, REF, "o", labels[1], "(a)"), (ax[1], new, NEW, "s", labels[0], "(b)")):
        z = per_coil(o, sim)
        a.plot(lim, lim, color="#222222", lw=.8)
        for f in (.5, 2):
            a.plot(lim, (lim[0] * f, lim[1] * f), color="#999999", lw=.6, ls="--")
        a.scatter(z.obs, z.sim.clip(lower=1), s=11, c=col, marker=mk, alpha=.75, lw=0)
        a.set(xscale="log", yscale="log", xlim=lim, ylim=lim, xlabel="Observed (veh/day)", ylabel="Simulated (veh/day)", title=f"{t} {lab}")
        a.set_aspect("equal")
        a.text(.04, .96, f"$\\rho_s$ = {spearmanr(z.obs, z.sim)[0]:.2f}", transform=a.transAxes, va="top")
    a = ax[2]
    for sim, col, mk, lab in ((ref, REF, "o", labels[1]), (new, NEW, "s", labels[0])):
        z = per_coil(o, sim)
        a.scatter(dist.reindex(z.index).clip(lower=.1), np.log10(z.sim.clip(lower=1) / z.obs), s=11, c=col, marker=mk, alpha=.65, lw=0, label=lab)
    a.axhline(0, color="#222222", lw=.8)
    a.set(xscale="log", xlabel="Distance to municipal point (km)", ylabel="log$_{10}$(sim/obs)", title="(c) Error vs distance")
    a.set_ylim(-1.0, .65)
    a.legend(frameon=False, loc="lower left")
    for e, kw in (("pdf", {}), ("svg", {}), ("png", {"dpi": 200})):
        fig.savefig(path.with_suffix("." + e), **kw)


def main():
    ref_dir, k_new, k_ref = Path(sys.argv[1]), f"k{float(sys.argv[2]):.1f}", f"k{float(sys.argv[3]):.1f}"
    new_dir = C.BASE
    o, new = C.load(sorted({f"k{x:.1f}" for x in C.GRID} | {k_new}))
    C.BASE = ref_dir
    o2, ref = C.load([k_ref])
    C.BASE = new_dir
    assert o[["coil", "day"]].equals(o2[["coil", "day"]])
    a, b, obs, coil = new[k_new], ref[k_ref], o.obs.values, o.coil.values
    u = np.unique(coil)
    idx = {c: np.where(coil == c)[0] for c in u}
    rng = np.random.default_rng(SEED)
    boot = []
    for _ in range(N_BOOT):
        i = np.concatenate([idx[c] for c in rng.choice(u, len(u))])
        boot.append(sd_log(a[i], obs[i]) - sd_log(b[i], obs[i]))
    ci = [float(x) for x in np.percentile(boot, [2.5, 97.5])]
    dist = municipal_distance(new_dir, k_new, u)
    rc = road_class(new_dir, k_new, o)
    dn, _ = diagnosis(o, a, dist, rc)
    dr, _ = diagnosis(o, b, dist, rc)
    out = {"reference": str(ref_dir.name), "k_new": k_new, "k_reference": k_ref, "detectors": int(len(u)), "rows": int(len(o)),
           "new": metrics(o, a), "reference_metrics": metrics(o, b),
           "new_other_k": {k: metrics(o, new[k]) for k in new if k != k_new},
           "sd_difference": sd_log(a, obs) - sd_log(b, obs), "sd_difference_ci95": ci, "rule_met": bool(ci[1] < 0),
           "by_day": {day: {"new": metrics(o[o.day == day], a[o.day == day]), "reference": metrics(o[o.day == day], b[o.day == day]),
                            "new_loss_by_k": {k: metrics(o[o.day == day], new[k][o.day == day])["mean_sq_log10"] for k in new}}
                      for day in o.day.unique()},
           "alive_23h": {"new": alive_23h(new_dir, k_new), "reference": alive_23h(ref_dir, k_ref)},
           "diagnosis_new": dn, "diagnosis_reference": dr}
    (D.RES / "calibration_round_comparison.json").write_text(json.dumps(out, indent=1) + "\n")
    figure(o, a, b, dist, (f"New, {k_new}", f"{ref_dir.name}, {k_ref}"), D.RES / "calibration_round_comparison.pdf")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
