#!/usr/bin/env python3
"""Figures of the Results not produced by make_figures.py.

fig_level   : province factors and simulated against observed daily volume at independent detectors
fig_sources : change brought by each source, with 95% intervals
fig_single  : how stable the error of a single road is, and what explains it
fig_factorial : relations and province factors in a 2x2 design
tables/od_factorial, experiments_* : tables of the experiments, from model/results/experiments

  python3 results_figures.py   -> model/manuscript/figures/fig_{level,sources,single}.{pdf,png}
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calibrate_demand as C  # noqa: E402
import demand_scaling as D  # noqa: E402
import od_matrix as M  # noqa: E402
import single_road_error as E  # noqa: E402
import validation_tests as V  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402
from paths import ARTICLE, RESULTS  # noqa: E402

C20, C21, GREY, INK = "#1F7F8C", "#C8693F", "#9e9e9e", "#252525"
PROV = {"PI": "Piacenza", "PA": "Parma", "RE": "Reggio Emilia", "MO": "Modena", "BO": "Bologna", "FE": "Ferrara", "RA": "Ravenna", "FO": "Forlì–Cesena", "RI": "Rimini"}
plt.rcParams.update({"font.size": 8.5, "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": 0.6, "pdf.fonttype": 42, "font.family": "sans-serif"})


def js(name):
    return json.load(open(RESULTS / name))


def save(fig, name):
    for ext in ("pdf", "png"):
        fig.savefig(ARTICLE / "figures" / f"{name}.{ext}", bbox_inches="tight", dpi=300)


def fig_level():
    f = js("demand/province_demand.json")["factors"]["2"]
    t20, t21 = V.table_2020()[0], V.table_2021()[0]
    fig, ax = plt.subplots(1, 3, figsize=(7.2, 2.6), constrained_layout=True, gridspec_kw=dict(width_ratios=[1, 1.1, 1.1]))
    s = sorted(f, key=f.get)
    ax[0].hlines(range(len(s)), 1, [f[k] for k in s], color=GREY, lw=1)
    ax[0].plot([f[k] for k in s], range(len(s)), "o", color=INK, ms=4)
    for i, k in enumerate(s):
        ax[0].text(f[k] + (0.05 if f[k] >= 1 else -0.05), i, f"{f[k]:.2f}", va="center", ha="left" if f[k] >= 1 else "right", fontsize=7.5)
    ax[0].axvline(1, color=GREY, lw=0.6, ls="--")
    ax[0].set_yticks(range(len(s)), [PROV[k] for k in s])
    ax[0].set(xlabel="Province factor", xlim=(0, 2.15), title="(a) Province factors")
    out = {}
    for a, t, col, mk, lab in [(ax[1], t20, C20, "o", "(b) Test half, February 2020"), (ax[2], t21, C21, "s", "(c) All detectors, June–July 2021")]:
        lim = np.array([1e3, 1.5e5])
        a.plot(lim, lim, color=INK, lw=0.8, ls="--")
        a.plot(lim, lim * 2, color=GREY, lw=0.6, ls=":")
        a.plot(lim, lim / 2, color=GREY, lw=0.6, ls=":")
        z = t[t.sim >= 1]
        a.scatter(z.obs, z.sim, s=9, color=col, marker=mk, lw=0, alpha=0.8)
        a.set(xscale="log", yscale="log", xlim=lim, ylim=lim, xlabel="Observed daily vehicles", title=f"{lab}\n{len(t)} detectors")
        a.set_aspect("equal")
        out[lab[:3]] = dict(n=len(t), zero=int((t.sim < 1).sum()), within2=float((np.abs(np.log10(z.sim / z.obs)) < np.log10(2)).sum() / len(t)))
    ax[1].set_ylabel("Simulated daily vehicles")
    save(fig, "fig_level")
    return out


def forest(a, rows, xlabel, title):
    y = np.arange(len(rows))[::-1]
    for yi, (lab, mid, ci, col, mk) in zip(y, rows):
        a.plot(ci, [yi, yi], color=col, lw=1.2)
        a.plot(mid, yi, mk, color=col, ms=4)
    a.axvline(0, color=INK, lw=0.7, ls="--")
    a.set_yticks(y, [r[0] for r in rows])
    a.set(xlabel=xlabel, title=title)


def fig_sources():
    p, o = js("demand/province_demand.json"), js("demand/source_value.json")["comparison"]
    vv, rc = js("demand/volume_validation.json")["2020_test_groups"]["outside_FC"], js("corrected/routing_comparison.json")
    b, l = js("corrected/detector_baselines.json")["leave_one_out"], js("corrected/loo_summary.json")
    new, old = p["test"]["round2"]["new"], p["test"]["round2"]["frozen"]
    n21, o21 = p["confirmation_2021"]["new"], p["confirmation_2021"]["frozen"]
    MON, SAT = C.CAL_DAYS
    h, a21 = "held_out_2020", "all_2021"
    f2 = js("experiments/e2_factorial.json")
    od = lambda key, ci: [(f"OD relations, {y}, {lab}", f2[day][s]["relations_with_factors"][key], f2[day][s]["relations_with_factors"][ci], c, m) for y, s, c, m in (("2020", h, C20, "o"), ("2021", a21, C21, "s")) for day, lab in ((MON, "Mon"), (SAT, "Sat"))]
    sp = [("GPS routing, 2020", vv["V6_minus_V0"]["spearman"], vv["V6_minus_V0"]["ci95"]["spearman"], C20, "o"),
          ("GPS routing, 2021", rc["2021"]["diff"], rc["2021"]["diff_ci95"], C21, "s"),
          ("Province factors, 2020", new["spearman"] - old["spearman"], p["test"]["round2"]["spearman_diff_ci95"], C20, "o"),
          ("Province factors, 2021", n21["spearman"] - o21["spearman"], p["confirmation_2021"]["spearman_diff_ci95"], C21, "s")] + od("spearman_diff", "spearman_diff_ci95")
    sd = [("Province factors, 2020", new["sd_log10"] - old["sd_log10"], p["test"]["round2"]["sd_diff_ci95"], C20, "o"),
          ("Province factors, 2021", n21["sd_log10"] - o21["sd_log10"], p["confirmation_2021"]["sd_diff_ci95"], C21, "s")] + od("sd_diff", "sd_diff_ci95")
    er = [(f"Correction vs raw, {y}", -l[y]["pooled_reduction_pp"], [-x for x in l[y]["bootstrap95_reduction_pp"][::-1]], c, m) for y, c, m in (("2020", C20, "o"), ("2021", C21, "s"))]
    er += [(f"Raw vs predictor, {y}", b[y]["raw_pct"] - b[y]["baseline_pct"], b[y]["raw_minus_baseline_ci95_pp"], c, m) for y, c, m in (("2020", C20, "o"), ("2021", C21, "s"))]
    er += [(f"Correction vs predictor, {y}", b[y]["loo_pct"] - b[y]["baseline_pct"], b[y]["loo_minus_baseline_ci95_pp"], c, m) for y, c, m in (("2020", C20, "o"), ("2021", C21, "s"))]
    fig, ax = plt.subplots(1, 3, figsize=(7.2, 2.7), constrained_layout=True)
    forest(ax[0], sp, "Change in Spearman correlation", "(a) Ranking of roads\n(right of zero: better)")
    forest(ax[1], sd, "Change in dispersion", "(b) Spread of the error\n(left of zero: better)")
    forest(ax[2], er, "Difference in hourly error (pp)", "(c) Error at left-out detectors\n(left of zero: first term better)")
    save(fig, "fig_sources")
    return dict(spearman=[(r[0], round(r[1], 3), np.round(r[2], 3).tolist()) for r in sp], sd=[(r[0], round(r[1], 3), np.round(r[2], 3).tolist()) for r in sd], err=[(r[0], round(r[1], 2), np.round(r[2], 2).tolist()) for r in er])


def fig_single():
    model = lambda d: D.OUT / "V6_scaled"
    w, a, allt = js("demand/single_road_error.json"), js("demand/single_road_error_province.json"), D.group_observations()
    MON, SAT = C.CAL_DAYS
    t = M.table("cal")
    days = pd.concat([E.resid(t, model, MON), E.resid(t, model, SAT)], axis=1, keys=["m", "s"]).dropna()
    l = pd.read_csv(RESULTS / "corrected/loo_detectors.csv").dropna(subset=["raw_total"])
    l = l[l.day.str.startswith("2021")].groupby(["coil", "day"])[["obs_total", "raw_total"]].sum().groupby("coil").mean()
    years = pd.concat([E.resid(allt, model, MON), np.log10(l.raw_total.clip(lower=1) / l.obs_total)], axis=1, keys=["a", "b"]).dropna()
    assert abs(days.m.corr(days.s) - a["persistence"]["monday_saturday"]["r"]) < 1e-6
    assert abs(years.a.corr(years.b) - a["persistence"]["winter_2020_summer_2021"]["r"]) < 1e-6
    fig, ax = plt.subplots(2, 2, figsize=(6.6, 5.2), constrained_layout=True)
    ax = ax.ravel()
    for x, xx, yy, col, mk, xl, yl, tt, r in [(ax[0], days.m, days.s, INK, "o", "Weekday error", "Weekend error", "(a) Between day types", a["persistence"]["monday_saturday"]), (ax[1], years.a, years.b, INK, "o", "Winter 2020 error", "Summer 2021 error", "(b) Between seasons", a["persistence"]["winter_2020_summer_2021"])]:
        lim = [-1.05, 0.75]
        x.plot(lim, lim, color=GREY, lw=0.7, ls="--")
        x.scatter(xx, yy.clip(lower=lim[0]), s=7, color=col, marker=mk, lw=0, alpha=0.7)
        x.set(xlim=lim, ylim=lim, xlabel=xl + r" ($\log_{10}$)", ylabel=yl + r" ($\log_{10}$)", title=f"{tt}\n$r$ = {r['r']:.2f}, {r['detectors']} detectors")
        x.set_aspect("equal")
    labs = [("province", "Province"), ("road_class", "Road class"), ("observed_volume", "Volume"), ("all_three", "All three")]
    y = np.arange(len(labs))
    ax[2].bar(y - 0.19, [100 * w["variance_explained_monday"][k] for k, _ in labs], 0.38, color=GREY, label="without factors")
    ax[2].bar(y + 0.19, [100 * a["variance_explained_monday"][k] for k, _ in labs], 0.38, color=C20, label="with factors")
    ax[2].set_xticks(y, [v for _, v in labs], rotation=35, ha="right")
    ax[2].set(ylabel="Variance explained (%)", title="(c) What explains it\n ")
    ax[2].legend(frameon=False, fontsize=7.5, loc="upper left")
    bins = list(a["neighbours"])
    x = np.arange(len(bins))
    n = [a["neighbours"][b]["null_ci95"] for b in bins]
    ax[3].fill_between(x, [v[0] for v in n], [v[1] for v in n], color="#e4e4e4", lw=0, label="chance")
    ax[3].plot(x, [w["neighbours"][b]["r"] for b in bins], "s--", color=GREY, ms=3, lw=1, label="without factors")
    ax[3].plot(x, [a["neighbours"][b]["r"] for b in bins], "o-", color=C20, ms=3, lw=1.2, label="with factors")
    ax[3].axhline(0, color=INK, lw=0.5)
    ax[3].set_xticks(x, [b.replace("km", "") for b in bins], rotation=35, ha="right")
    ax[3].set(xlabel="Distance between detectors (km)", ylabel="Correlation of errors", title="(d) Between neighbours\n ")
    ax[3].legend(frameon=False, fontsize=7.5, loc="upper right")
    save(fig, "fig_single")


def fig_factorial():
    e = js("experiments/e2_factorial.json")
    MON, SAT = C.CAL_DAYS
    cases = [(MON, "held_out_2020", "Test half 2020, Monday"), (SAT, "held_out_2020", "Test half 2020, Saturday"), (MON, "all_2021", "2021, Monday"), (SAT, "all_2021", "2021, Saturday")]
    fig, ax = plt.subplots(2, 4, figsize=(7.2, 3.6), constrained_layout=True, sharex=True, sharey="row")
    for j, (d, s, lab) in enumerate(cases):
        x = e[d][s]
        w, n = x["relations_with_factors"], x["relations_without_factors"]
        for i, (a_, b_, yl) in enumerate((("sd_a", "sd_b", "Dispersion"), ("spearman_a", "spearman_b", "Spearman correlation"))):
            ax[i, j].plot([0, 1], [n[a_], w[a_]], "o-", color=C20, ms=4, lw=1.3, label="with OD relations")
            ax[i, j].plot([0, 1], [n[b_], w[b_]], "s--", color=C21, ms=4, lw=1.3, label="without OD relations")
            ax[i, j].set_xticks([0, 1], ["no factors", "factors"])
            ax[i, j].set_xlim(-0.3, 1.3)
            if j == 0:
                ax[i, j].set_ylabel(yl)
        ax[0, j].set_title(lab, fontsize=9)
    ax[1, 0].legend(frameon=False, fontsize=7.5, loc="lower right")
    save(fig, "fig_factorial")


def fig_od():
    e2, pa = js("experiments/e2_factorial.json"), js("experiments/od_pairing.json")
    MON, SAT = C.CAL_DAYS
    cases = [("held_out_2020", MON, "2020 Mon", C20, "o"), ("held_out_2020", SAT, "2020 Sat", C20, "o"), ("all_2021", MON, "2021 Mon", C21, "s"), ("all_2021", SAT, "2021 Sat", C21, "s")]
    groups = [("Relations removed, factors kept", lambda s, d: e2[d][s]["relations_with_factors"]), ("Null M, 50 municipalities", ("N50", "M")), ("Null D, 50 municipalities", ("N50", "D")), ("Null D, 347 municipalities", ("N347", "D"))]
    fig, ax = plt.subplots(1, 2, figsize=(7.0, 4.0), constrained_layout=True, sharey=True)
    labels, y = [], 0
    for name, g in groups:
        for s, d, lab, col, mk in cases:
            if callable(g):
                x = g(s, d)
                vals = [(x["sd_diff"], x["sd_diff_ci95"]), (x["spearman_diff"], x["spearman_diff_ci95"])]
            else:
                z = pa[g[0]][d][s]
                w = z[g[1]]
                vals = [(z["real"]["sd"] - w["null_mean"]["sd"], w["real_minus_null_sd_ci95"]), (z["real"]["spearman"] - w["null_mean"]["spearman"], w["real_minus_null_spearman_ci95"])]
            for a, (m, c) in zip(ax, vals):
                a.plot(c, [y, y], color=col, lw=1.2)
                a.plot(m, y, mk, color=col, ms=3.5)
            labels.append((y, f"{name}: {lab}" if lab == "2020 Mon" else lab))
            y -= 1
        y -= 0.8
    for a in ax:
        a.axvline(0, color=INK, lw=0.7, ls="--")
    ax[0].set_yticks([v for v, _ in labels], [l.split(": ")[-1] for _, l in labels], fontsize=9)
    for v, l in labels:
        if ": " in l:
            ax[0].text(0.0, v + 0.72, l.split(": ")[0], transform=ax[0].get_yaxis_transform(), fontsize=7.5, fontweight="bold", ha="left", va="center")
    ax[0].set(xlabel="Change in dispersion", title="(a) Spread of the error (left of zero: real relations better)")
    ax[1].set(xlabel="Change in Spearman correlation", title="(b) Ranking of roads (right of zero: real relations better)")
    ax[0].title.set_fontsize(9); ax[1].title.set_fontsize(9)
    save(fig, "fig_od")


def tables():
    T = ARTICLE / "tables"
    MON, SAT = C.CAL_DAYS
    e2 = js("experiments/e2_factorial.json")
    iv = lambda v, n=3: f"[{v[0]:+.{n}f}, {v[1]:+.{n}f}]"
    cases = [("Test half, 2020", "held_out_2020", MON, "Monday"), ("Test half, 2020", "held_out_2020", SAT, "Saturday"), ("2021", "all_2021", MON, "Monday"), ("2021", "all_2021", SAT, "Saturday")]
    rows = []
    for lab, s, d, dl in cases:
        x = e2[d][s]
        r, f = x["relations_with_factors"], x["factors_without_relations"]
        rows.append(f"{lab} & {dl} & {r['spearman_diff']:+.3f} {iv(r['spearman_diff_ci95'])} & {r['sd_diff']:+.3f} {iv(r['sd_diff_ci95'])} & {f['sd_diff']:+.3f} {iv(f['sd_diff_ci95'])} \\\\")
    (T / "od_factorial.tex").write_text("\\begin{tabular}{@{}llccc@{}}\\toprule\n & & \\multicolumn{2}{c}{OD relations, with factors} & Factors, no relations \\\\\nDetectors & Day & Spearman & Dispersion & Dispersion \\\\\\midrule\n" + "\n".join(rows) + "\n\\bottomrule\\end{tabular}\n")
    pa = js("experiments/od_pairing.json")
    rows = []
    for cov, kind, lab in (("N50", "M", "M, 50"), ("N50", "D", "D, 50"), ("N347", "D", "D, 347")):
        for s_, sl in (("held_out_2020", "Test half, 2020"), ("all_2021", "2021")):
            for d, dl in ((MON, "Monday"), (SAT, "Saturday")):
                z = pa[cov][d][s_]
                w = z[kind]
                rows.append(f"{lab} & {sl} & {dl} & {z['n']} & {z['real']['sd']:.3f} & {w['null_mean']['sd']:.3f} & {iv(w['real_minus_null_sd_ci95'])} & {z['real']['spearman']:.3f} & {w['null_mean']['spearman']:.3f} & {iv(w['real_minus_null_spearman_ci95'])} & {w['sensitivity_median_abs_log10']:.3f} & {iv(w['twin_sd_ci95'])} \\\\")
    (T / "od_pairing.tex").write_text("\\begin{tabular}{@{}lllrrrlrrlrl@{}}\\toprule\nNull & Detectors & Day & $n$ & \\multicolumn{3}{c}{Dispersion: real, null, difference} & \\multicolumn{3}{c}{Spearman: real, null, difference} & Sens. & Twin, disp. \\\\\\midrule\n" + "\n".join(rows) + "\n\\bottomrule\\end{tabular}\n")
    cc = js("experiments/e3_correction_curve.json")["by_fraction"]
    rows = [f"{r['day']} & {100 * r['frac']:.0f} & {r['n']:.0f} & {r['raw']:.1f} & {r['corrected']:.1f} & {r['raw'] - r['corrected']:+.1f} & [{r['min_gain']:+.1f}, {r['max_gain']:+.1f}] \\\\" for r in cc]
    (T / "experiments_curve.tex").write_text("\\begin{tabular}{@{}lrrrrrl@{}}\\toprule\nDay & Share (\\%) & Detectors & Raw (\\%) & Corrected (\\%) & Gain (pp) & Range over repeats \\\\\\midrule\n" + "\n".join(rows) + "\n\\bottomrule\\end{tabular}\n")
    e4 = js("experiments/e4_routing.json")
    names = [("V0", "Shortest distance, default speeds"), ("V1", "Shortest distance, GPS speeds"), ("V2", "Travel time, GPS speeds"), ("V3", "Mixed distance/time, GPS speeds"), ("V4", "Travel time + class weights"), ("V5", "Travel time + damped class weights"), ("D1", "Usage cost + class weights, default speeds"), ("V6", "Usage cost + class weights (selected)")]
    rows = []
    for k, lab in names:
        a, b = e4["gps"][MON], e4["gps"][SAT]
        ci = lambda g: iv(g["other_minus_V6_ci95"][k]) if k != "V6" else "--"
        rows.append(f"{lab} & {a['spearman'][k]:.3f} & {ci(a)} & {b['spearman'][k]:.3f} & {ci(b)} \\\\")
    (T / "experiments_routing.tex").write_text("\\begin{tabular}{@{}lrlrl@{}}\\toprule\nVariant & Monday & minus selected & Saturday & minus selected \\\\\\midrule\n" + "\n".join(rows) + "\n\\bottomrule\\end{tabular}\n")
    rows = []
    for s, lab in (("held_out_2020_outside_FC", "Test half, 2020"), ("all_2021_outside_FC", "2021")):
        for d, dl in ((MON, "Monday"), (SAT, "Saturday")):
            x = e4["detectors"][d][s]
            p = x["pairs"]
            rows.append(f"{lab} & {dl} & {x['n']} & {x['spearman']['V0']:.2f} & {x['spearman']['V1']:.2f} & {x['spearman']['D1']:.2f} & {x['spearman']['V6']:.2f} & {iv(p['V1_vs_V0']['spearman_ci95'], 2)} & {iv(p['D1_vs_V0']['spearman_ci95'], 2)} & {iv(p['V6_vs_D1']['spearman_ci95'], 2)} \\\\")
    (T / "experiments_separation.tex").write_text("\\begin{tabular}{@{}llrrrrrlll@{}}\\toprule\nDetectors & Day & $n$ & V0 & V1 & D1 & V6 & V1$-$V0 & D1$-$V0 & V6$-$D1 \\\\\\midrule\n" + "\n".join(rows) + "\n\\bottomrule\\end{tabular}\n")
    rows = [f"{a} & {c['new']['sd_log10']:.3f} & {c['new']['spearman']:.3f} & {iv(c['sd_diff_ci95'])} \\\\" for a, c in ((n[2:].replace("_", ", "), v) for n, v in e4["alpha"].items())]
    (T / "experiments_alpha.tex").write_text("\\begin{tabular}{@{}lrrl@{}}\\toprule\nWeights & Dispersion & Spearman & Change in dispersion \\\\\\midrule\n" + "\n".join(rows) + "\n\\bottomrule\\end{tabular}\n")


if __name__ == "__main__":
    print(fig_level())
    print(json.dumps(fig_sources()))
    fig_single()
    fig_factorial()
    fig_od()
    tables()
