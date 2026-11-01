#!/usr/bin/env python3
"""Choice of the demand scale k by day type, on the calibration detectors (radius 20 km, without province factors).

Reads the simulations of radius_scan.py and adds to the losses of radius_scan_refined.json the volume ratio and the
paired bootstrap over detectors of each k against the selected one.

  python3 k_choice_figure.py   -> model/results/demand/k_choice_curve.json, model/manuscript/figures/figS_k_choice.{pdf,png}
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calibrate_demand as C  # noqa: E402
import demand_scaling as D  # noqa: E402
import radius_scan as S  # noqa: E402
from paths import ARTICLE  # noqa: E402

N_BOOT, SEED = 2000, 20261047
GRID = [0.7, 0.8, 0.9, 1.0, 1.1, 1.2]
SELECTED = {"2020-02-10": 1.0, "2020-02-15": 0.8}
STYLE = {"2020-02-10": ("#1F7F8C", "o", "Weekdays (Monday run)"), "2020-02-15": ("#C8693F", "s", "Weekends (Saturday run)")}


def curve():
    C.BASE = S.BASE / "r20"
    o, cols = C.load([f"k{k:.1f}" for k in GRID])
    rng = np.random.default_rng(SEED)
    out = {}
    for day in C.CAL_DAYS:
        z = (o.day == day).values
        obs, coil = o.obs.values[z], o.coil.values[z]
        err = {k: np.log10(np.clip(cols[f"k{k:.1f}"][z], 1, None) / obs) ** 2 for k in GRID}
        boot = {k: [] for k in GRID}
        for _ in range(N_BOOT):
            i = rng.integers(0, len(obs), len(obs))
            for k in GRID:
                boot[k].append(err[k][i].mean())
        boot = {k: np.array(v) for k, v in boot.items()}
        wins = np.array([boot[k] for k in GRID]).argmin(axis=0)
        sel = SELECTED[day]
        out[day] = {"detectors": int(len(np.unique(coil))), "selected": sel, "by_k": {
            f"{k:.1f}": {"loss": float(err[k].mean()), "ratio": float(cols[f"k{k:.1f}"][z].sum() / obs.sum()),
                         "loss_minus_selected_ci95": [float(x) for x in np.percentile(boot[k] - boot[sel], [2.5, 97.5])],
                         "share_resamples_best": float((wins == j).mean())} for j, k in enumerate(GRID)}}
    (D.RES / "k_choice_curve.json").write_text(json.dumps(out, indent=1) + "\n")
    return out


def figure(res):
    plt.rcParams.update({"font.size": 7.5, "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": 0.6,
                         "pdf.fonttype": 42, "font.family": "sans-serif"})
    fig, (a, b, c) = plt.subplots(1, 3, figsize=(7.0, 2.4), constrained_layout=True)
    for day, r in res.items():
        col, mk, lab = STYLE[day]
        v = r["by_k"]
        ci = np.array([v[f"{k:.1f}"]["loss_minus_selected_ci95"] for k in GRID])
        kw = dict(color=col, marker=mk, ms=3.5, lw=1.2)
        a.plot(GRID, [v[f"{k:.1f}"]["loss"] for k in GRID], label=lab, **kw)
        s = v[f"{r['selected']:.1f}"]
        a.plot(r["selected"], s["loss"], marker=mk, ms=8, mfc="none", mec=col, mew=1.0)
        shift = -0.008 if day == C.CAL_DAYS[0] else 0.008
        mid = [(x + y) / 2 for x, y in ci]
        c.errorbar(np.array(GRID) + shift, mid, yerr=[np.subtract(mid, ci[:, 0]), np.subtract(ci[:, 1], mid)], fmt=mk, ms=3, color=col, lw=0.9)
        b.plot(GRID, [v[f"{k:.1f}"]["ratio"] for k in GRID], **kw)
        b.plot(r["selected"], s["ratio"], marker=mk, ms=8, mfc="none", mec=col, mew=1.0)
    a.set(xlabel="$k$", ylabel=r"Mean squared $\log_{10}$(simulated/observed)", title="(a) Loss")
    h, l = a.get_legend_handles_labels()
    b.legend(h, l, frameon=False, fontsize=6.5, loc="lower right")
    b.axhline(1, color="#888888", lw=0.6, ls="--")
    b.set(xlabel="$k$", ylabel="Simulated / observed volume", title="(b) Volume ratio")
    c.axhline(0, color="#888888", lw=0.6, ls="--")
    c.set(xlabel="$k$", ylabel="Loss minus loss at selected $k$", title="(c) Paired difference, 95% interval")
    for ax in (a, b, c):
        ax.set_xticks(GRID)
    for ext in ("pdf", "png"):
        fig.savefig(ARTICLE / "figures" / f"figS_k_choice.{ext}", bbox_inches="tight", dpi=300)


if __name__ == "__main__":
    res = curve()
    figure(res)
    for day, r in res.items():
        print(day, r["detectors"], r["selected"])
        for k, v in r["by_k"].items():
            print(" ", k, round(v["loss"], 4), round(v["ratio"], 3), np.round(v["loss_minus_selected_ci95"], 4), round(v["share_resamples_best"], 3))
