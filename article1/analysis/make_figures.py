#!/usr/bin/env python3
"""Figures for Article 1 from the corrected reconstruction (run after reconstruct_and_validate.py).

fig3_reconstruction : (a) coil 282, 10 Feb 2020, raw / assimilated / observed; (b) daily link flows
fig4_gps            : (a,b) GPS-matched links in 2020 and 2021; (c) GPS-to-simulation ratio
fig5_validation     : hourly-share MAE distributions (all days; weekday/weekend)
fig6_diagnostics    : pooled hourly profiles; held-out detector errors
"""
import json
import os
from pathlib import Path

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection

A1 = Path(__file__).resolve().parents[1]
ROOT = A1.parent
SIM = Path(os.environ.get("SIM_DIR", "/home/fede/sim_runs/routing/V6_gps_usage_classweights"))  # final configuration
RES = A1 / "results/corrected"
PRIV = A1 / "results/private"
FIG = A1 / "figures"
CARTO = A1 / "results/carto_a059fb0.geojson"
C = {"assim": "#1F7F8C", "raw": "#C8693F", "gps": "#252525", "od": "#8c8c8c", "mts": "#545454"}
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                     "pdf.fonttype": 42, "savefig.dpi": 300, "font.family": "sans-serif"})


def save(fig, name):
    for ext in ("pdf", "png"):
        fig.savefig(FIG / f"{name}.{ext}", bbox_inches="tight", dpi=300)
    plt.close(fig)


def lines(gdf):
    return [np.asarray(g.coords) for g in gdf.geometry]


def daily_flows(day):
    f = SIM / f"sim_{day}_uniq_{day}_000000.csv.corrected"
    d = pd.read_csv(f, sep=";")
    cols = [c for c in d if c.startswith("20")]
    return d.groupby("poly_cid")[cols].sum().sum(axis=1)


def fig3(carto):
    day = "200210"
    raw = pd.read_csv(SIM / f"sim_{day}_uniq_{day}_000000.csv", sep=";")
    asm = pd.read_csv(SIM / f"sim_{day}_uniq_{day}_000000.csv.corrected", sep=";")
    cols = [c for c in raw if c.startswith("20")]
    obs = pd.read_csv(ROOT / "data/old_coils_data/_coils_table_200201-000000_200331-234500.csv", sep=";", index_col=0)
    obs.index = pd.to_datetime(obs.index, utc=True).tz_convert("Europe/Rome").tz_localize(None)
    obs = obs[obs.index.normalize() == pd.Timestamp("2020-02-10")]
    obs = obs[["282_0", "282_1"]].sum(axis=1).groupby(obs.index.hour).sum()
    bar = pd.read_csv(ROOT / "vars/extra/er_barriers_cartodata.csv", sep=";")
    lid = int(bar.loc[bar.tag == 282, "poly_lid"].iloc[0])
    pc = int(raw.loc[raw.poly_lid == lid, "poly_cid"].iloc[0])
    r = raw[raw.poly_cid == pc][cols].sum().values
    a = asm[asm.poly_cid == pc][cols].sum().values
    fig = plt.figure(figsize=(10, 4.2), constrained_layout=True)
    gs = fig.add_gridspec(1, 2, width_ratios=[1, 1.25])
    ax = fig.add_subplot(gs[0])
    h = np.arange(24)
    ax.plot(h, obs.reindex(h).values, "o-", color=C["gps"], ms=3, label=f"Coil 282 (observed, {obs.sum():,.0f})")
    ax.plot(h, r, "-", color=C["raw"], label=f"Raw simulation ({r.sum():,.0f})")
    ax.plot(h, a, "--", color=C["assim"], label=f"Assimilated ({a.sum():,.0f})")
    ax.set(xlabel="Hour (local time, interval start)", ylabel=r"Hourly flow $\Phi$ (vehicles)", xticks=range(0, 24, 3),
           title="(a) Link of coil 282, both directions, 10 Feb 2020")
    ax.legend(fontsize=8, frameon=False)
    ax2 = fig.add_subplot(gs[1])
    q = daily_flows(day)
    g = carto.set_index("poly_cid").join(q.rename("flow")).fillna({"flow": 0})
    ranks = g.flow.rank(pct=True)
    order = np.argsort(ranks.values)
    lc = LineCollection([lines(g)[i] for i in order], array=ranks.values[order], cmap="viridis",
                        linewidths=0.4 + 1.6 * ranks.values[order])
    ax2.add_collection(lc)
    ax2.autoscale(); ax2.set_aspect("equal"); ax2.axis("off")
    cb = fig.colorbar(lc, ax=ax2, shrink=0.6, label="Daily flow quantile")
    ax2.set_title("(b) Assimilated daily link flows, 10 Feb 2020")
    save(fig, "fig3_reconstruction")
    return dict(coil282_obs=float(obs.sum()), coil282_raw=float(r.sum()), coil282_assim=float(a.sum()),
                coil282_raw_corr=float(np.corrcoef(r, obs.reindex(h).values)[0, 1]),
                coil282_peak_obs=int(obs.idxmax()), coil282_peak_raw=int(np.argmax(r)))


def fig4(carto):
    fig = plt.figure(figsize=(10, 4.2), constrained_layout=True)
    gs = fig.add_gridspec(1, 3, width_ratios=[1, 1, 0.9])
    base = lines(carto)
    out = {}
    for j, year in enumerate([2020, 2021]):
        m = pd.read_csv(PRIV / f"corrected_link_metrics_{year}_all.csv")
        ax = fig.add_subplot(gs[j])
        ax.add_collection(LineCollection(base, colors="#d9d9d9", linewidths=0.4))
        sel = carto[carto.poly_cid.isin(m.cid)]
        ax.add_collection(LineCollection(lines(sel), colors=C["assim"], linewidths=1.0))
        ax.autoscale(); ax.set_aspect("equal"); ax.axis("off")
        ax.set_title(f"({chr(97 + j)}) GPS-matched links, {year} ({len(m)})")
        out[year] = dict(links=len(m), median_ratio=float((m.gps_total / m.sim_total).median()))
    ax = fig.add_subplot(gs[2])
    bins = np.linspace(-5, 0, 41)
    for year, col in [(2020, C["assim"]), (2021, C["raw"])]:
        m = pd.read_csv(PRIV / f"corrected_link_metrics_{year}_all.csv")
        ax.hist(np.log10(m.gps_total / m.sim_total), bins=bins, histtype="step", lw=1.4, color=col, label=str(year))
    ax.set(xlabel=r"$\log_{10}\eta_i$ (GPS probes / simulated vehicles)", ylabel="Links", title="(c) Probe-to-simulation ratio")
    ax.legend(frameon=False)
    save(fig, "fig4_gps")
    return out


def cdf(ax, v, **kw):
    v = np.sort(v)
    ax.step(v, np.arange(1, len(v) + 1) / len(v), where="post", **kw)


def fig5():
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), constrained_layout=True)
    for j, year in enumerate([2020, 2021]):
        m = pd.read_csv(PRIV / f"corrected_link_metrics_{year}_all.csv")
        ax = axes[0, j]
        for col, lab, c, ls in [("mae_pp", "Assimilated", C["assim"], "-"), ("mae_pp_raw", "Raw simulation", C["raw"], "-"),
                                ("mae_pp_od", "OD demand profile", C["od"], ":"), ("mae_pp_mts", "Mean MTS profile", C["mts"], "--")]:
            cdf(ax, m[col], color=c, ls=ls, label=lab)
        ax.set(xlim=(0, 6), xlabel="Hourly-share MAE (percentage points)", ylabel="Fraction of links",
               title=f"({chr(97 + j)}) {year}, all days, {len(m)} links")
        ax.legend(fontsize=8, frameon=False)
        ax = axes[1, j]
        for kind, c in [("weekday", C["assim"]), ("weekend", C["raw"])]:
            z = pd.read_csv(PRIV / f"corrected_link_metrics_{year}_{kind}.csv")
            cdf(ax, z.mae_pp, color=c, label=f"{kind.capitalize()}, reconstruction")
            cdf(ax, z.mae_pp_mts, color=c, ls="--", lw=0.9, label=f"{kind.capitalize()}, MTS profile")
        ax.set(xlim=(0, 6), xlabel="Hourly-share MAE (percentage points)", ylabel="Fraction of links",
               title=f"({chr(99 + j)}) {year}, weekdays and weekends")
        ax.legend(fontsize=8, frameon=False)
    save(fig, "fig5_validation")


def fig6():
    fig = plt.figure(figsize=(10, 9), constrained_layout=True)
    gs = fig.add_gridspec(3, 2, height_ratios=[1, 1, 1.1])
    for j, year in enumerate([2020, 2021]):
        ax = fig.add_subplot(gs[j, 0])
        d = pd.read_csv(RES / f"aggregate_profiles_{year}.csv")
        for col, lab, c, ls in [("sim_share", "Reconstruction", C["assim"], "-"), ("gps_share", "GPS probes", C["gps"], "-"),
                                ("mts_share", "Mean MTS profile", C["mts"], "--")]:
            ax.plot(d.hour, 100 * d[col], color=c, ls=ls, label=lab)
        ax.set(xlabel="Hour (local time, interval start)", ylabel="Hourly share (%)", xticks=range(0, 24, 3),
               title=f"({chr(97 + j)}) {year}, all usable links pooled")
        ax.legend(fontsize=8, ncol=3, frameon=False)
    ax = fig.add_subplot(gs[2, :])
    e = pd.read_csv(RES / "error_vs_detector_distance.csv")
    for year, c, off in [(2020, C["assim"], -0.18), (2021, C["raw"], 0.18)]:
        z = e[e.year == year]
        x = np.arange(len(z))
        ax.bar(x + off, z.gain_pp, width=0.34, color=c, label=f"{year}")
        for xi, n in zip(x, z.links):
            ax.text(xi + off, 0.005, str(n), ha="center", va="bottom", fontsize=6, rotation=90, color="white")
    ax.set_xticks(np.arange(len(z)), z.hop_class)
    ax.axhline(0, color="k", lw=0.6)
    ax.set(xlabel="Network distance from the nearest detector (polylines)",
           ylabel="Median MAE reduction (pp)", title="(d) Effect of assimilation on GPS links")
    ax.legend(frameon=False)
    ax = fig.add_subplot(gs[:2, 1])
    d = pd.read_csv(RES / "loo_detectors.csv").dropna(subset=["loo_abs", "raw_abs"])
    hi = 0
    for year, c, mk in [("2020", C["assim"], "o"), ("2021", C["raw"], "s")]:
        z = d[d.day.str.startswith(year)]
        by = z.groupby("coil")[["obs_total", "raw_abs", "loo_abs"]].sum()
        x, y = 100 * by.raw_abs / by.obs_total, 100 * by.loo_abs / by.obs_total
        ax.scatter(x, y, s=14, color=c, marker=mk, alpha=0.75, label=f"{year} ({len(by)} detectors)")
        hi = max(hi, x.quantile(0.98), y.quantile(0.98))
    hi *= 1.05
    ax.plot([0, hi], [0, hi], "k--", lw=0.8)
    ax.set(xlim=(0, hi), ylim=(0, hi), xlabel="Held-out error, raw simulation (% of observed volume)",
           ylabel="Held-out error, other detectors assimilated (%)", title="(c) Leave-one-detector-out")
    ax.set_aspect("equal", adjustable="box")
    ax.legend(fontsize=8, frameon=False)
    save(fig, "fig6_diagnostics")


def fig7():
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import volume_check as V
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.6), constrained_layout=True)
    cmp = json.load(open(RES / "routing_comparison.json"))
    for j, year in enumerate([2020, 2021]):
        ax = axes[j]
        for sim_dir, lab, c, mk in [("/home/fede/sim_runs/carto2024", "Shortest-distance routing", C["od"], "o"),
                                    (str(SIM), "GPS-informed routing", C["assim"], "s")]:
            _, r = V.run(sim_dir, year, "raw")
            r = r[r.prov != "FO"]
            key = "spearman_base" if "carto2024" in sim_dir else "spearman_gps"
            ax.scatter(r.obs, r.sim.clip(lower=1), s=12, alpha=0.7, color=c, marker=mk,
                       label=f"{lab} ($\\rho_s$ = {cmp[str(year)][key]:.2f})")
        lim = [1e3, 1e5]
        ax.plot(lim, lim, "k--", lw=0.8)
        ax.plot(lim, [l / 2 for l in lim], "k:", lw=0.6)
        ax.plot(lim, [l * 2 for l in lim], "k:", lw=0.6)
        ax.set(xscale="log", yscale="log", xlim=lim, ylim=[1e2, 1e5],
               xlabel="Observed daily vehicles (MTS detector)", ylabel="Simulated daily vehicles (raw)",
               title=f"({chr(97 + j)}) {year}, {cmp[str(year)]['detectors']} detectors outside Forli-Cesena")
        ax.legend(fontsize=8, frameon=False, loc="upper left")
    save(fig, "fig7_volumes")


def main():
    carto = gpd.read_file(CARTO)
    info = {"fig3": fig3(carto), "fig4": fig4(carto)}
    fig5()
    fig6()
    fig7()
    (RES / "figure_numbers.json").write_text(json.dumps(info, indent=2, default=float) + "\n")
    print(json.dumps(info, indent=1, default=float))


if __name__ == "__main__":
    main()
