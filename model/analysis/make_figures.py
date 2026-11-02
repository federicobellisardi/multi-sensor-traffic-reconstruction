#!/usr/bin/env python3
"""Figures for Article 1 from the corrected reconstruction (run after reconstruct_and_validate.py).

fig3_reconstruction : (a) coil 282 withheld from the correction, hourly counts, 10 Feb 2020; (b) daily link flows
fig4_gps            : (a,b) GPS-matched links in 2020 and 2021; (c) GPS-to-simulation ratio
fig5_validation     : hourly-share MAE distributions, Forli-Cesena links, all days; fig5b_daytypes: weekdays and weekends
fig6_diagnostics    : pooled hourly profiles; effect of the correction by distance from the nearest detector
fig7_volumes        : daily volumes at withheld detectors

Maps use the CARTO basemap when CARTO_API_KEY is set.
"""
import contextlib
import io
import json
import os
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_input_figures import basemap  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import ARTICLE as A1, RESULTS as R1, SIM_RUNS  # noqa: E402

SIM = Path(os.environ.get("SIM_DIR", SIM_RUNS / "demand/V6_scaled"))  # final configuration (demand_scaling.py)
RES = R1 / "corrected"
PRIV = R1 / "private"
FIG = A1 / "figures"
CARTO = R1 / "carto_a059fb0.geojson"
C = {"assim": "#1F7F8C", "raw": "#C8693F", "gps": "#252525", "od": "#8c8c8c", "mts": "#545454"}
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                     "pdf.fonttype": 42, "savefig.dpi": 300, "font.family": "sans-serif"})


def save(fig, name):
    for ext in ("pdf", "png"):
        fig.savefig(FIG / f"{name}.{ext}", bbox_inches="tight", dpi=300)
    plt.close(fig)


def fc_metrics(path):
    """Link metrics restricted to the GPS links of Forli-Cesena."""
    import gps_validation_split as G
    m = pd.read_csv(path)
    return m[m.cid.isin(G.fc_links())]


def lines(gdf):
    return [np.asarray(g.coords) for g in gdf.geometry]


def daily_flows(day):
    f = SIM / f"sim_{day}_uniq_{day}_000000.csv.corrected"
    d = pd.read_csv(f, sep=";")
    cols = [c for c in d if c.startswith("20")]
    return d.groupby("poly_cid")[cols].sum().sum(axis=1)


def best_withheld():
    """Detector with the lowest error of the leave-one-out test on 10 Feb 2020, chosen as the best case, and the error of all."""
    d = pd.read_csv(RES / "loo_detectors.csv").dropna(subset=["raw_abs", "loo_abs"])
    x = d[d.day == "2020-02-10"].groupby("coil").agg(obs=("obs_total", "sum"), loo=("loo_abs", "sum"))
    return int((x.loo / x.obs).idxmin()), len(x), float(100 * (x.loo / x.obs).median())


def coil_withheld(coil):
    """Detector withheld from the correction of 10 Feb 2020 (all other coils assimilated)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import reconstruct_and_validate as P
    sim = P.corrector(str(SIM / "sim_200210"))
    pcid = sim.coil2poly[coil]
    sim.poly2coil = {k: v for k, v in sim.poly2coil.items() if k != pcid}
    with contextlib.redirect_stdout(io.StringIO()):
        f = sim.correct([t for t in sim.dfb.tag.values if sim.coil2poly[t] != pcid], suffix=f"withheld{coil}")
    d = pd.read_csv(f, sep=";")
    cols = [c for c in d if c.startswith("20")]
    rec = d[d.poly_cid == pcid][cols].sum()
    rec.index = pd.to_datetime(rec.index)
    obs = sim.dfc[[f"{coil}_IN", f"{coil}_OUT"]].sum(axis=1)
    return rec, obs.reindex(rec.index)


def fig3(carto):
    day = "200210"
    coil, n, median_error = best_withheld()
    rec, obs = coil_withheld(coil)
    hrs = rec.index.hour
    fig = plt.figure(figsize=(10, 4.2), constrained_layout=True)
    gs = fig.add_gridspec(1, 2, width_ratios=[1, 1.25])
    ax = fig.add_subplot(gs[0])
    ax.plot(hrs, obs.values, "o-", ms=3, color=C["gps"], lw=1.2, label=f"Detector {coil}, observed ({obs.sum():,.0f})")
    ax.plot(hrs, rec.values, "s-", ms=3, color=C["assim"], lw=1.2, label=f"Reconstruction, detector left out ({rec.sum():,.0f})")
    ax.set(xlim=(-0.5, 23.5), xticks=range(0, 24, 3), xlabel="Hour (local time, interval start), 10 February 2020",
           ylabel="Vehicles per hour, both directions", title="(a) Best case: prediction at a left-out detector")
    ax.set_ylim(0, 1.25 * max(obs.max(), rec.max()))
    ax.legend(fontsize=8, frameon=False, loc="upper left")
    ax2 = fig.add_subplot(gs[1])
    q = daily_flows(day)
    g = carto.to_crs(3857).set_index("poly_cid").join(q.rename("flow")).fillna({"flow": 0})
    ranks = g.flow.rank(pct=True)
    order = np.argsort(ranks.values)
    lc = LineCollection([lines(g)[i] for i in order], array=ranks.values[order], cmap="viridis",
                        linewidths=0.4 + 1.6 * ranks.values[order], zorder=2)
    ax2.add_collection(lc)
    ax2.autoscale(); ax2.set_aspect("equal"); ax2.axis("off")
    basemap(ax2)
    fig.colorbar(lc, ax=ax2, shrink=0.6, label="Daily flow quantile")
    ax2.set_title("(b) Reconstructed daily link flows, 10 Feb 2020")
    save(fig, "fig3_reconstruction")
    err = np.abs(rec.values - obs.values).sum() / obs.sum()
    return dict(best_coil=coil, detectors_that_day=n, median_directional_error_pct=median_error, best_obs=float(obs.sum()), best_withheld=float(rec.sum()),
                best_corr_hourly=float(np.corrcoef(rec.values, obs.values)[0, 1]),
                best_abs_error_pct=float(100 * err),
                best_peak_obs=int(obs.values.argmax()), best_peak_rec=int(rec.values.argmax()))


def fig4(carto):
    fig = plt.figure(figsize=(10, 4.2), constrained_layout=True)
    gs = fig.add_gridspec(1, 3, width_ratios=[1, 1, 0.9])
    carto = carto.to_crs(3857)
    base = lines(carto)
    out = {}
    for j, year in enumerate([2020, 2021]):
        m = fc_metrics(PRIV / f"corrected_link_metrics_{year}_all.csv")
        ax = fig.add_subplot(gs[j])
        ax.add_collection(LineCollection(base, colors="#9e9e9e", linewidths=0.4, zorder=2))
        sel = carto[carto.poly_cid.isin(m.cid)]
        ax.add_collection(LineCollection(lines(sel), colors=C["assim"], linewidths=1.0, zorder=3))
        ax.autoscale(); ax.set_aspect("equal"); ax.axis("off")
        basemap(ax)
        ax.set_title(f"({chr(97 + j)}) GPS links of Forlì–Cesena, {year} ({len(m)})")
        out[year] = dict(links=len(m), median_ratio=float((m.gps_total / m.sim_total).median()))
    ax = fig.add_subplot(gs[2])
    bins = np.linspace(-5, 0, 41)
    for year, col in [(2020, C["assim"]), (2021, C["raw"])]:
        m = fc_metrics(PRIV / f"corrected_link_metrics_{year}_all.csv")
        ax.hist(np.log10(m.gps_total / m.sim_total), bins=bins, histtype="step", lw=1.4, color=col, label=str(year))
    ax.set(xlabel=r"$\log_{10}\eta_i$ (GPS probes / simulated vehicles)", ylabel="Links", title="(c) Probe-to-simulation ratio")
    ax.legend(frameon=False)
    save(fig, "fig4_gps")
    return out


def cdf(ax, v, **kw):
    v = np.sort(v)
    ax.step(v, np.arange(1, len(v) + 1) / len(v), where="post", **kw)


def fig5():
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6), constrained_layout=True)
    fig2, axes2 = plt.subplots(1, 2, figsize=(10, 3.6), constrained_layout=True)
    for j, year in enumerate([2020, 2021]):
        m = fc_metrics(PRIV / f"corrected_link_metrics_{year}_all.csv")
        ax = axes[j]
        for col, lab, c, ls in [("mae_pp", "Reconstruction", C["assim"], "-"),
                                ("mae_pp_od", "OD demand profile", C["od"], ":"), ("mae_pp_mts", "Mean detector profile", C["mts"], "--")]:
            cdf(ax, m[col], color=c, ls=ls, label=lab)
        ax.set(xlim=(0, 6), xlabel="Hourly-share MAE (percentage points)", ylabel="Fraction of links",
               title=f"({chr(97 + j)}) {year}, all days, {len(m)} links")
        ax.legend(fontsize=8, frameon=False)
        ax = axes2[j]
        for kind, c in [("weekday", C["assim"]), ("weekend", C["raw"])]:
            z = fc_metrics(PRIV / f"corrected_link_metrics_{year}_{kind}.csv")
            cdf(ax, z.mae_pp, color=c, label=f"{kind.capitalize()}, reconstruction")
            cdf(ax, z.mae_pp_mts, color=c, ls="--", lw=0.9, label=f"{kind.capitalize()}, detector profile")
        ax.set(xlim=(0, 6), xlabel="Hourly-share MAE (percentage points)", ylabel="Fraction of links",
               title=f"({chr(97 + j)}) {year}, weekdays and weekends")
        ax.legend(fontsize=8, frameon=False)
    save(fig, "fig5_validation")
    save(fig2, "fig5b_daytypes")


def fig6():
    fig = plt.figure(figsize=(10, 6.6), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 0.9])
    for j, year in enumerate([2020, 2021]):
        ax = fig.add_subplot(gs[0, j])
        d = pd.read_csv(RES / f"aggregate_profiles_{year}.csv")
        for col, lab, c, ls in [("sim_share", "Reconstruction", C["assim"], "-"), ("gps_share", "GPS probes", C["gps"], "-"),
                                ("mts_share", "Mean detector profile", C["mts"], "--")]:
            ax.plot(d.hour, 100 * d[col], color=c, ls=ls, label=lab)
        ax.set(xlabel="Hour (local time, interval start)", ylabel="Hourly share (%)", xticks=range(0, 24, 3),
               title=f"({chr(97 + j)}) {year}, all usable links pooled")
        ax.legend(fontsize=8, frameon=False)
    ax = fig.add_subplot(gs[1, :])
    e = pd.read_csv(RES / "error_vs_detector_distance.csv")
    for year, c, off in [(2020, C["assim"], -0.18), (2021, C["raw"], 0.18)]:
        z = e[e.year == year]
        x = np.arange(len(z))
        ax.bar(x + off, z.gain_pp, width=0.34, color=c, label=f"{year}")
        for xi, n in zip(x, z.links):
            ax.text(xi + off, max(z.gain_pp.max(), 0.05) * 0.02, str(n), ha="center", va="bottom", fontsize=6, rotation=90,
                    color="white" if z.gain_pp.iloc[int(xi)] > 0.06 else "black")
    ax.set_xticks(np.arange(len(z)), z.hop_class)
    ax.axhline(0, color="k", lw=0.6)
    ax.set(xlabel="Network distance from the nearest detector (links)",
           ylabel="Median MAE reduction (pp)", title="(c) Effect of the detector correction on GPS links")
    ax.legend(frameon=False)
    save(fig, "fig6_diagnostics")


def fig7():
    """Daily volumes at withheld detectors: observed against the reconstruction with all other detectors assimilated."""
    d = pd.read_csv(RES / "loo_detectors.csv").dropna(subset=["loo_total"])
    loo = json.load(open(RES / "loo_summary.json"))
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.6), constrained_layout=True)
    lim = [1e3, 2e5]
    for j, year in enumerate(["2020", "2021"]):
        ax = axes[j]
        z = d[d.day.str.startswith(year)]
        cd = z.groupby(["coil", "day"]).agg(obs=("obs_total", "sum"), rec=("loo_total", "sum"), reached=("changed", "any"))
        by = cd.groupby("coil").agg(obs=("obs", "mean"), rec=("rec", "mean"), reached=("reached", "any"))
        for reached, c, mk, lab in [(False, C["od"], "o", "not reached by the correction"), (True, C["assim"], "s", "reached by the correction")]:
            b = by[by.reached == reached]
            ax.scatter(b.obs, b.rec.clip(lower=lim[0] / 10), s=13, alpha=0.75, color=c, marker=mk, label=f"{lab} ({len(b)})")
        ax.plot(lim, lim, "k--", lw=0.8)
        ax.plot(lim, [l / 2 for l in lim], "k:", lw=0.6)
        ax.plot(lim, [l * 2 for l in lim], "k:", lw=0.6)
        rho = by.rec.corr(by.obs, method="spearman")
        ax.set(xscale="log", yscale="log", xlim=lim, ylim=[lim[0] / 10, lim[1]],
               xlabel="Observed daily vehicles", ylabel="Reconstructed daily vehicles, detector left out",
               title=f"({chr(97 + j)}) {year}, {len(by)} detectors, $\\rho_s$ = {rho:.2f}")
        ax.legend(fontsize=8, frameon=False, loc="upper left")
    save(fig, "fig7_volumes")


def fig8():
    """Volume ratio by road class over all detectors; also returns the numbers of the hourly error before and after the correction."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import detector_baselines as B
    d = pd.read_csv(RES / "loo_detectors.csv").dropna(subset=["raw_abs", "loo_abs"])
    d["year"] = d.day.str[:4]
    by = d.groupby(["year", "coil"]).agg(obs=("obs_total", "sum"), raw=("raw_total", "sum"), raw_abs=("raw_abs", "sum"), loo_abs=("loo_abs", "sum")).reset_index()
    by["err_raw"], by["err_loo"], by["ratio"] = 100 * by.raw_abs / by.obs, 100 * by.loo_abs / by.obs, by.raw / by.obs
    by["road"] = B.CLS.reindex(B.BAR.reindex(by.coil).values).values
    col = {"2020": "#1F7F8C", "2021": "#C8693F"}
    style = dict(patch_artist=True, widths=0.32, flierprops=dict(marker="o", ms=2.5, mfc="#444444", mec="#444444", mew=0, alpha=0.7), medianprops=dict(color="k", lw=1.2), whiskerprops=dict(lw=0.7), capprops=dict(lw=0.7), boxprops=dict(lw=0.6))
    fig, b = plt.subplots(figsize=(5.6, 3.4), constrained_layout=True)
    out = {}
    for y in ("2020", "2021"):
        z = by[by.year == y]
        out[y] = dict(detectors=int(len(z)), median_raw=float(z.err_raw.median()), median_corrected=float(z.err_loo.median()), iqr_corrected=[float(z.err_loo.quantile(q)) for q in (.25, .75)])
    classes = [c for c in ("trunk", "primary", "secondary", "tertiary") if c in set(by.road)]
    z = by[by.ratio > 0]
    out["zero_simulated"] = int((by.ratio <= 0).sum())
    for i, c in enumerate(classes):
        for j, y in enumerate(("2020", "2021")):
            v = z[(z.road == c) & (z.year == y)].ratio
            p = b.boxplot([v], positions=[i + (j - 0.5) * 0.4], **style)
            p["boxes"][0].set(facecolor=col[y], alpha=0.8)
            b.text(i + (j - 0.5) * 0.4, 0.14, str(len(v)), ha="center", fontsize=7)
    b.axhline(1, color="k", lw=0.8, ls="--")
    for v in (0.5, 2):
        b.axhline(v, color="k", lw=0.5, ls=":")
    b.set(yscale="log", ylim=(0.12, 12), xticks=range(len(classes)), xticklabels=classes, ylabel="Simulated / observed daily volume", title="Volume ratio by road class, raw simulation")
    b.set_yticks([0.25, 0.5, 1, 2, 4, 8], ["0.25", "0.5", "1", "2", "4", "8"])
    b.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=col[y], alpha=0.8, label=y) for y in col], frameon=False, loc="upper right")
    save(fig, "fig8_distributions")
    return out


def main():
    carto = gpd.read_file(CARTO)
    info = {"fig3": fig3(carto), "fig4": fig4(carto)}
    fig5()
    fig6()
    fig7()
    info["fig8"] = fig8()
    (RES / "figure_numbers.json").write_text(json.dumps(info, indent=2, default=float) + "\n")
    print(json.dumps(info, indent=1, default=float))


if __name__ == "__main__":
    main()
