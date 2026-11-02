#!/usr/bin/env python3
"""Held-out detectors against the frozen raw simulation, weekdays and weekend separately. Nothing is to be selected on this.

Daily volumes: hourly uniq of radius_scan.py at 20 km and the k of the day type, against round 7 (10 km, k = 1.2).
Flow at 15 min: barriers of the runs with cam_dump_dt = 900, both directions summed.

  python3 frozen_validation.py config    write the configurations into $SIM_RUNS/frozen_q15/
  python3 frozen_validation.py evaluate  -> model/results/demand/frozen_validation.{json,pdf,svg,png}
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calibrate_demand as C  # noqa: E402
import delay_quarter as Q  # noqa: E402
import demand_scaling as D  # noqa: E402
import demand_scan_eval as E  # noqa: E402

OUT = D.RUNS / "final_q15"
FROZEN = D.RUNS / "province_demand/round2"
REF = D.RUNS / "calibration_round7"
EXAMPLE = 282
OBS, SIM = "#222222", "#D55E00"
N_BOOT, SEED = 2000, 20261040
NAMES = {"2020-02-10": "Weekdays", "2020-02-15": "Weekend"}


def config():
    OUT.mkdir(parents=True, exist_ok=True)
    for day in C.CAL_DAYS:
        c = json.load(open(FROZEN / f"sim_{D.tag(day)}.json"))
        c["cam_dump_dt"] = 900
        c["state_basename"] = str(OUT / f"sim_{D.tag(day)}")
        json.dump(c, open(OUT / f"sim_{D.tag(day)}.json", "w"), indent=1)
        print(OUT / f"sim_{D.tag(day)}.json")


def daily():
    g = D.group_observations()
    u = g.drop_duplicates("coil").reset_index(drop=True)
    calib = set(u.coil[E.split(u)])
    o = g[~g.coil.isin(calib)].reset_index(drop=True)
    get = lambda base, k, d: D.link_daily(next((base / f"k{k:.1f}").glob(f"sim_{D.tag(d)}_uniq_*.csv")))
    new = np.array([D.link_daily(next(FROZEN.glob(f"sim_{D.tag(d)}_uniq_*.csv"))).get(l, 0.0) for d, l in o[["day", "poly_lid"]].values])
    ref = new if D.NO_CODE else np.array([get(REF, 1.2, d).get(l, 0.0) for d, l in o[["day", "poly_lid"]].values])
    obs, coil = o.obs.values, o.coil.values
    def m(s, b):
        lr = np.log10(np.clip(s[b], 1, None) / obs[b])
        return {"n": int(b.sum()), "ratio": float(s[b].sum() / obs[b].sum()), "spearman": float(spearmanr(obs[b], s[b])[0]), "sd_log10": float(lr.std()),
                "median_abs_log10": float(np.median(np.abs(lr))), "within_factor2": float(np.mean(np.abs(lr) < np.log10(2)))}
    us = np.unique(coil)
    idx = {c: np.where(coil == c)[0] for c in us}
    rng = np.random.default_rng(SEED)
    sd = lambda s, i: np.log10(np.clip(s[i], 1, None) / obs[i]).std()
    d = [sd(new, i) - sd(ref, i) for i in (np.concatenate([idx[c] for c in rng.choice(us, len(us))]) for _ in range(N_BOOT))]
    res = {"all": {"frozen": m(new, np.ones(len(o), bool)), "round7": m(ref, np.ones(len(o), bool))},
           "sd_frozen_minus_round7_ci95": [float(x) for x in np.percentile(d, [2.5, 97.5])]}
    for day in C.CAL_DAYS:
        b = (o.day == day).values
        res[NAMES[day]] = {"frozen": m(new, b), "round7": m(ref, b)}
    return res


def quarter(day):
    Q.DAY = day
    coil, obs, sim = Q.load(OUT, check=False, test=True)
    err = 100 * np.abs(sim - obs).sum(axis=1) / obs.sum(axis=1)
    hour = 100 * np.abs(Q.hourly(sim) - Q.hourly(obs)).sum(axis=1) / obs.sum(axis=1)
    curve = {q: Q.err(obs, Q.shifted(sim, q)) for q in Q.SHIFTS}
    corr = np.array([np.corrcoef(a, b)[0, 1] if b.std() > 0 else np.nan for a, b in zip(obs, sim)])
    po, so = obs.sum(axis=0), sim.sum(axis=0)
    r = {"detectors": int(len(obs)), "ratio_barriers": float(sim.sum() / obs.sum()),
         "pooled_error_15min_pct": float(100 * np.abs(sim - obs).sum() / obs.sum()), "pooled_error_hourly_pct": float(Q.err(obs, sim)),
         "error_15min_quartiles_pct": [float(x) for x in np.percentile(err, [25, 50, 75])],
         "error_hourly_quartiles_pct": [float(x) for x in np.percentile(hour, [25, 50, 75])],
         "profile_correlation_quartiles": [float(x) for x in np.nanpercentile(corr, [25, 50, 75])],
         "remaining_best_shift_quarters": min(curve, key=curve.get), "oracle_level_error_hourly_pct": float(Q.err(obs, Q.rescale(obs, sim))),
         "peaks_obs_am_sim_am_obs_pm_sim_pm": [Q.peak(po, 5, 12), Q.peak(so, 5, 12), Q.peak(po, 14, 21), Q.peak(so, 14, 21)]}
    order = np.argsort(err)
    picks = [(f"rank {i + 1} of {len(order)}", int(order[i])) for i in range(4)]  # best cases, the distribution is in fig8
    panels = [(lab, int(coil[i]), obs[i], sim[i], float(sim[i].sum() / obs[i].sum()), float(err[i]), float(corr[i])) for lab, i in picks]
    r["shown"] = {str(p[1]): {"label": p[0], "ratio": p[4], "error_15min_pct": p[5], "correlation": p[6]} for p in panels}
    return r, panels


def evaluate():
    out = {"k_weekday": D.k_of("2020-02-10"), "k_weekend": D.k_of("2020-02-15"), "radius_km": D.CHERRY_RADIUS_KM,
           "shift_quarters": D.DEPARTURE_SHIFT_QUARTERS, "daily": daily()}
    plt.rcParams.update({"font.size": 7.5, "font.family": "sans-serif", "axes.linewidth": .6, "axes.spines.top": False,
                         "axes.spines.right": False, "pdf.fonttype": 42, "svg.fonttype": "none"})
    fig, ax = plt.subplots(2, 4, figsize=(7.2, 4.4), constrained_layout=True)
    t = np.arange(96) / 4
    for row, day in enumerate(C.CAL_DAYS):
        r, panels = quarter(day)
        out[NAMES[day]] = r
        for a, (lab, c, o, s, ratio, e, cr) in zip(ax[row], panels):
            a.plot(t, o, color=OBS, lw=1.2, label="Detector")
            a.plot(t, s, color=SIM, lw=1.1, ls="--", label="Simulation")
            a.set(xticks=range(0, 25, 6), xlim=(0, 24), ylim=(0, None))
            a.set_title(f"{NAMES[day]}, detector {c}\n{lab.lower()}\nratio {ratio:.2f}, error {e:.0f}%, r {cr:.2f}", fontsize=6)
        for a in ax[row, len(panels):]:
            a.axis("off")
        ax[row, 0].set_ylabel("Flow, both directions (veh/15 min)")
    for a in ax[1]:
        a.set_xlabel("Hour (interval start)")
    fig.legend(*ax[0, 0].get_legend_handles_labels(), frameon=False, loc="outside lower center", ncol=2, fontsize=7)
    for e, kw in (("pdf", {}), ("svg", {}), ("png", {"dpi": 200})):
        fig.savefig(D.RES / f"frozen_validation.{e}", **kw)
    (D.RES / "frozen_validation.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    {"config": config, "evaluate": evaluate}[sys.argv[1]]()
