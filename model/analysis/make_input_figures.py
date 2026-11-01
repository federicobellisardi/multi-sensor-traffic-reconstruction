#!/usr/bin/env python3
"""Input figures for Article 1, rebuilt from the simulation inputs of the final configuration.

fig1_inputs : (a) project graph by OSM road class; (b) observed trip ends of the injected demand by
              municipality; (c) MTS detectors on the graph, by use in calibration and validation; (d) 15-min counts of coil 282, 10 Feb 2020
fig2_demand : (a) hourly agents generated on a weekday and on a weekend day; (b) demand classes;
              (c) municipalities with most observed trip ends

Usage: CARTO_API_KEY=... python3 model/analysis/make_input_figures.py   (SIM_DIR as in make_figures.py;
without a key the maps are drawn without basemap)
"""
import json
import os
from collections import Counter, defaultdict
from pathlib import Path

import contextily as cx
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import ROOT, ARTICLE as A1, RESULTS as R1, SIM_RUNS  # noqa: E402

SIM = Path(os.environ.get("SIM_DIR", SIM_RUNS / "demand/V6_scaled"))
FIG = A1 / "figures"
RES = R1
WEEKDAY, WEEKEND = "200210", "200215"
CLASSES = {"scr_dest": "Both ends known, municipalities", "scr_dest_prov": "Both ends known, provinces",
           "src_rnd": "Origin known, destination random", "rnd_dest": "Destination known, origin random", "rnd_rnd": "Both ends random"}
CLASS_COL = {"scr_dest": "#1F7F8C", "scr_dest_prov": "#7FB8BF", "src_rnd": "#C8693F", "rnd_dest": "#E3A982", "rnd_rnd": "#8c8c8c"}
ROAD = [("motorway", "#7a1f1f", 1.4), ("trunk", "#C8693F", 1.1), ("primary", "#1F7F8C", 0.8),
        ("secondary", "#6f6f6f", 0.5), ("tertiary", "#a8a8a8", 0.4), ("other", "#cfcfcf", 0.35)]
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                     "pdf.fonttype": 42, "savefig.dpi": 300, "font.family": "sans-serif"})


def save(fig, name):
    for ext in ("pdf", "png"):
        fig.savefig(FIG / f"{name}.{ext}", bbox_inches="tight", dpi=300)
    plt.close(fig)


def demand(day):
    """Agents per 15-min bin by class, and observed trip ends by municipality."""
    src = json.load(open(SIM / f"sim_{day}.json"))["sources"]
    by_class = defaultdict(lambda: np.zeros(96))
    ends = Counter()
    for name, s in src.items():
        rate = np.asarray(s["creation_rate"][:96], float)  # agents per 15-min bin
        for p in s["pawns"]:
            by_class[p] += rate
        if "scr_dest_prov" in s["pawns"]:  # province-level relations with neighbouring regions
            continue
        parts = name.split("_")
        if "source_location" in s:
            ends[municipality(parts[0])] += rate.sum()
        if "dest_location" in s:
            ends[municipality(parts[1] if "source_location" in s else parts[0])] += rate.sum()
    return dict(by_class), ends


def locations(day):
    src = json.load(open(SIM / f"sim_{day}.json"))["sources"]
    loc = {}
    for name, s in src.items():
        parts = name.split("_")
        if "source_location" in s:
            loc[municipality(parts[0])] = s["source_location"]
        if "dest_location" in s:
            loc[municipality(parts[1] if "source_location" in s else parts[0])] = s["dest_location"]
    return loc


def basemap(ax, zoom=8):
    key = os.environ.get("CARTO_API_KEY")
    if key:
        url = "https://basemaps.cartocdn.com/rastertiles/light_nolabels/{z}/{x}/{y}.png?key=" + key
        cx.add_basemap(ax, crs="EPSG:3857", source=url, attribution=False, zoom=zoom)
    return bool(key)


def municipality(name):
    """Source names spell some municipalities with and without spaces (Reggio nell'Emilia)."""
    return name.replace(" ", "")


def label(key, names):
    return max((n for n in names if municipality(n) == key), key=len)


def detector_use():
    """Detector sets of the paper: calibration and test half of February 2020, detectors of the 2021 campaign."""
    import demand_scaling as D
    import demand_scan_eval as E
    u = D.group_observations().drop_duplicates("coil").reset_index(drop=True)
    in_cal = E.split(u)
    d = pd.read_csv(RES / "corrected/loo_detectors.csv")
    y2021 = set(d[d.day.str.startswith("2021")].dropna(subset=["raw_total"]).coil)
    return set(u.coil[in_cal]), set(u.coil[~in_cal]), y2021


def fig1():
    carto = gpd.read_file(RES / "carto_a059fb0.geojson").to_crs(3857)
    cls = pd.read_csv(RES / "road_class.csv").set_index("poly_cid").road_class
    carto["cls"] = carto.poly_cid.map(cls).where(lambda c: c.isin([r[0] for r in ROAD[:-1]]), "other")
    prov = gpd.read_file(ROOT / "vars/extra/er-shapes.geojson").to_crs(3857)
    bar = pd.read_csv(ROOT / "vars/extra/er_barriers_cartodata.csv", sep=";")
    bar = gpd.GeoDataFrame(bar, geometry=gpd.points_from_xy(bar.lon, bar.lat), crs=4326).to_crs(3857)
    fc = prov[prov.PRO_NAME.str.startswith("Forl")]
    calib, test, y2021 = detector_use()
    bar["use"] = np.where(bar.tag.isin(calib), "calibration", np.where(bar.tag.isin(test | y2021), "validation", "other"))
    xmin, ymin, xmax, ymax = prov.total_bounds
    pad = 0.02 * (xmax - xmin)

    fig = plt.figure(figsize=(10, 6.6), constrained_layout=True)
    gs = fig.add_gridspec(2, 2)
    axes = [fig.add_subplot(gs[i, j]) for i in range(2) for j in range(2)]
    for ax in axes[:3]:
        ax.set_xlim(xmin - pad, xmax + pad); ax.set_ylim(ymin - pad, ymax + pad)
        ax.set_aspect("equal"); ax.axis("off")
        if basemap(ax):
            prov.boundary.plot(ax=ax, color="#9e9e9e", lw=0.5, zorder=1)
        else:
            prov.plot(ax=ax, color="#f4f4f2", edgecolor="#9e9e9e", lw=0.5, zorder=1)

    ax = axes[0]
    for c, col, lw in reversed(ROAD):
        g = carto[carto.cls == c]
        ax.add_collection(LineCollection([np.asarray(x.coords) for x in g.geometry], colors=col, linewidths=lw, zorder=2))
    fc.boundary.plot(ax=ax, color="#252525", lw=1.0, zorder=3)
    ax.legend(handles=[Line2D([], [], color=col, lw=2, label=c) for c, col, _ in ROAD], loc="lower left",
              frameon=False, fontsize=7, ncol=2)
    km50 = 50e3 / np.cos(np.radians(44.5))  # web-Mercator units for 50 km at the latitude of the region
    ax.plot([xmax - 1.0e4 - km50, xmax - 1.0e4], [ymin + 1.5e4] * 2, color="k", lw=1.5)
    ax.text(xmax - 1.0e4 - km50 / 2, ymin + 2.2e4, "50 km", ha="center", fontsize=7)
    ax.set_title(f"(a) Road graph: {len(carto):,} links; Forlì–Cesena outlined", fontsize=9)

    ax = axes[1]
    _, ends = demand(WEEKDAY)
    loc = locations(WEEKDAY)
    m = pd.DataFrame([(k, v, loc[k]["lon"], loc[k]["lat"]) for k, v in ends.items() if k in loc], columns=["mun", "n", "lon", "lat"])
    m = gpd.GeoDataFrame(m, geometry=gpd.points_from_xy(m.lon, m.lat), crs=4326).to_crs(3857).sort_values("n", ascending=False)
    ax.add_collection(LineCollection([np.asarray(x.coords) for x in carto.geometry], colors="#d9d9d9", linewidths=0.3, zorder=2))
    ax.scatter(m.geometry.x, m.geometry.y, s=6 + 400 * m.n / m.n.max(), color="#C8693F", alpha=0.6, edgecolor="white", lw=0.3, zorder=3)
    for n in (1e4, 5e4, 2e5):
        ax.scatter([], [], s=6 + 400 * n / m.n.max(), color="#C8693F", alpha=0.6, label=f"{n:,.0f}")
    ax.legend(title="Trip ends per day", loc="lower left", frameon=False, fontsize=7, title_fontsize=7, labelspacing=1.1)
    ax.set_title(f"(b) Observed trip ends of the injected demand, weekday ({len(m)} municipalities)", fontsize=9)

    ax = axes[2]
    ax.add_collection(LineCollection([np.asarray(x.coords) for x in carto.geometry], colors="#bdbdbd", linewidths=0.3, zorder=2))
    for use, col, lab in [("other", "#9e9e9e", "other"), ("validation", "#1F7F8C", "validation"), ("calibration", "#C8693F", "calibration")]:
        b = bar[bar.use == use]
        ax.scatter(b.geometry.x, b.geometry.y, s=9, color=col, edgecolor="white", lw=0.3, zorder=4, label=f"{lab} ({len(b)})")
    h, l = ax.get_legend_handles_labels()
    ax.legend(h[::-1], l[::-1], loc="lower left", frameon=False, fontsize=7, title="Detectors", title_fontsize=7)
    ax.set_title(f"(c) Loop detectors on the graph ({len(bar)})", fontsize=9)

    ax = axes[3]
    obs = pd.read_csv(ROOT / "data/old_coils_data/_coils_table_200201-000000_200331-234500.csv", sep=";", index_col=0)
    obs.index = pd.to_datetime(obs.index, utc=True).tz_convert("Europe/Rome").tz_localize(None)
    obs = obs[obs.index.normalize() == pd.Timestamp("2020-02-10")][["282_0", "282_1"]]
    hrs = (obs.index - obs.index.normalize()).total_seconds() / 3600
    for c, col, lab in [("282_0", "#252525", "direction 0"), ("282_1", "#8c8c8c", "direction 1")]:
        ax.plot(hrs, obs[c], color=col, lw=1.2, label=lab)
    ax.set(xlim=(0, 24), xticks=range(0, 25, 3), xlabel="Local time, Monday 10 February 2020 (h)", ylabel="Vehicles per 15 min")
    ax.legend(frameon=False, loc="upper left")
    ax.set_title("(d) Counts of detector 282 (Bologna area)", fontsize=9)
    ins = ax.inset_axes([0.36, 0.63, 0.27, 0.36])
    c282 = bar[bar.tag == 282].geometry.iloc[0]
    half = 2.0e4
    ins.set_xlim(c282.x - half, c282.x + half); ins.set_ylim(c282.y - half, c282.y + half)
    ins.add_collection(LineCollection([np.asarray(x.coords) for x in carto.geometry], colors="#9e9e9e", linewidths=0.4, zorder=2))
    ins.scatter([c282.x], [c282.y], s=30, color="#C8693F", edgecolor="k", lw=0.6, zorder=4)
    ins.annotate("detector 282", (c282.x, c282.y), xytext=(5, 5), textcoords="offset points", fontsize=7, zorder=5)
    bo = gpd.GeoSeries(gpd.points_from_xy([11.3426], [44.4949]), crs=4326).to_crs(3857).iloc[0]
    ins.scatter([bo.x], [bo.y], s=12, marker="s", color="#252525", zorder=4)
    ins.annotate("Bologna", (bo.x, bo.y), xytext=(-4, -9), textcoords="offset points", fontsize=7, ha="right", zorder=5)
    if not basemap(ins, zoom=11):
        ins.set_facecolor("#f4f4f2")
    ins.set_xticks([]); ins.set_yticks([])
    for sp in ins.spines.values():
        sp.set_visible(True); sp.set_color("#6f6f6f"); sp.set_linewidth(0.6)
    ins.set_aspect("equal")
    if os.environ.get("CARTO_API_KEY"):
        fig.text(0.005, -0.01, "Basemap \u00a9 OpenStreetMap contributors \u00a9 CARTO", fontsize=6, color="#6f6f6f")
    save(fig, "fig1_inputs")
    return dict(polylines=len(carto), detectors=len(bar), detectors_use=bar.use.value_counts().to_dict(), calibration_also_2021=len(calib & y2021), municipalities=len(m))


def fig2():
    fig = plt.figure(figsize=(10, 3.6), constrained_layout=True)
    gs = fig.add_gridspec(1, 3, width_ratios=[1.3, 1, 0.9])
    out = {}
    ax = fig.add_subplot(gs[0])
    for day, col, lab in [(WEEKDAY, "#252525", "weekday"), (WEEKEND, "#8c8c8c", "weekend day")]:
        bc, _ = demand(day)
        tot = sum(bc.values()).reshape(24, 4).sum(axis=1)
        ax.plot(range(24), tot / 1e3, "o-", ms=3, color=col, label=lab)
        out[lab] = dict(agents=float(tot.sum()), shares={k: float(v.sum() / sum(x.sum() for x in bc.values())) for k, v in bc.items()})
    ax.set(xticks=range(0, 24, 3), xlabel="Hour of day (local time, start of hour)", ylabel="Generated agents per hour (thousands)")
    ax.legend(frameon=False)
    ax.set_title("(a) Injected demand, mean OD 13 Jan-23 Feb 2020", fontsize=9)

    ax = fig.add_subplot(gs[1])
    for j, (lab, col) in enumerate([("weekday", "#252525"), ("weekend day", "#8c8c8c")]):
        for i, k in enumerate(CLASSES):
            w = 100 * out[lab]["shares"].get(k, 0.0)
            ax.barh(i + (j - 0.5) * 0.38, w, height=0.36, color=col, label=lab if i == 0 else None)
            ax.text(w + 0.7, i + (j - 0.5) * 0.38, f"{w:.0f}", va="center", fontsize=7)
    ax.set(yticks=range(len(CLASSES)), yticklabels=[v.replace(", ", ",\n") for v in CLASSES.values()], xlim=(0, 46), xlabel="Share of generated agents (%)")
    ax.tick_params(axis="y", labelsize=7, length=0)
    ax.invert_yaxis()
    ax.set_title("(b) What is known of the trip ends", fontsize=9)

    ax = fig.add_subplot(gs[2])
    _, ends = demand(WEEKDAY)
    names = json.load(open(SIM / f"sim_{WEEKDAY}.json"))["sources"]
    names = {p for n in names for p in n.split("_")}
    top = pd.Series(ends).drop("LOCALS", errors="ignore").sort_values(ascending=False).head(15)[::-1]
    ax.barh([label(k, names) for k in top.index], top.values / 1e3, color="#1F7F8C")
    ax.set(xlabel="Trip ends per weekday (thousands)")
    ax.tick_params(axis="y", labelsize=7)
    ax.set_title("(c) Most active municipalities", fontsize=9)
    save(fig, "fig2_demand")
    return out


def main():
    nums = {"fig1": fig1(), "fig2": fig2()}
    (RES / "corrected/input_figure_numbers.json").write_text(json.dumps(nums, indent=2) + "\n")
    print(json.dumps(nums, indent=1))


if __name__ == "__main__":
    main()
