#!/usr/bin/env python3
"""Validation of the reconstructed hourly profiles against Viasat on all usable links.

Outputs (written to article/results/revision/):
  link_metrics_<year>.csv     one row per matched link
  validation_summary.json     summary numbers quoted in the manuscript
  representatives_2020.csv    links selected for the example panels
and the figures 10_validation_cdf, 7a/7b (normalised Ward clustering), 8a-8d
(representative links) and the penetration panels 6b/6c/6d in article/tex/images/.

Conventions
-----------
* minimocas labels every hourly dump with the start of the interval; the Viasat
  tables use the same convention, so simulated hour h is compared with Viasat hour h.
  The archived validation code shifted the simulation forward by 75 min (one hour
  bin); that variant is kept only as a sensitivity check (SHIFT_SENSITIVITY).
* eta_i is the ratio between Viasat probes and simulated vehicles summed over the
  same days.
* The profile error of link i is the mean absolute difference between hourly shares,
  MAE_i = (1/24) sum_h |p_sim(h) - p_gps(h)|, in percentage points. Relative to the
  mean hourly share 1/24 this is eps_i = sum_h |p_sim(h) - p_gps(h)|.
"""
import itertools
import json
import warnings
from pathlib import Path

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.cluster.hierarchy as sch
from matplotlib.lines import Line2D
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "article/results/revision"
IMG = ROOT / "article/tex/images"
OUT.mkdir(parents=True, exist_ok=True)

YEARS = {
    2020: dict(viasat=ROOT / "work_viasat/viasat_20200210_20200218_timed_fluxes.csv",
               sim=ROOT / "work_viasat/sim2020/uniq", exclude=[]),
    # The 2021 Viasat extract ends on Sunday 4 July; the archived 5 July run (a copy of
    # the 28 June configuration) is excluded so that both sides contain 5 weekdays + 2 weekend days.
    2021: dict(viasat=ROOT / "work_viasat/viasat_20210628_20210705_timed_fluxes.csv",
               sim=ROOT / "work_viasat/sim2021/uniq", exclude=["210705"]),
}
COILS_2020 = ROOT / "data/old_coils_data/_coils_table_200201-000000_200331-234500.csv"
COILS_AVE = ROOT / "data/coils_ave_220101-000000_221231-234500.csv"
CARTO = ROOT / "article/data/uniq/carto.geojson"
INNER_CLUSTER = ROOT / "work_viasat/viasat_data_analysis/2020/None/inner_cluster/inner_cluster_2.csv"
FIXED_REPRESENTATIVE = 104671
MIN_SEPARATION_KM = 40.0
H = np.arange(24)

plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
                     "savefig.dpi": 300, "pdf.fonttype": 42})
CLASS_COLORS = {-1: "#252525", -2: "#3182bd", -3: "#e6550d", -4: "#9e9ac8"}
SUB_COLORS = {0: "#545454", 1: "#C8693F", 2: "#1F7F8C"}


def save(fig, stem):
    for ext in ("png", "pdf"):
        fig.savefig(IMG / f"{stem}.{ext}", bbox_inches="tight", dpi=300)
    plt.close(fig)


def load_viasat(path):
    v = pd.read_csv(path, sep=";", parse_dates=["time"])
    days = sorted(v.time.dt.date.unique())
    hourly = v.groupby([v.time.dt.hour, "cid"]).total_fluxes.sum().unstack(fill_value=0)
    hourly = hourly.reindex(H, fill_value=0)
    hourly = hourly.loc[:, hourly.sum() > 0]
    weekday_days = sum(pd.Timestamp(d).dayofweek < 5 for d in days)
    return hourly, days, weekday_days


def sim_files(directory, exclude, corrected=True):
    pattern = "*_uniq_*.csv.corrected" if corrected else "*_uniq_??????_000000.csv"
    files = sorted(directory.glob(pattern))
    return [f for f in files if not any(f"_uniq_{d}" in f.name for d in exclude)]


def load_sim(files):
    frames = []
    for f in files:
        d = pd.read_csv(f, sep=";")
        cols = [c for c in d.columns if str(c).startswith("20")]
        g = d.groupby("poly_cid")[cols].sum().T
        g.index = pd.to_datetime(g.index).hour
        frames.append(g.groupby(level=0).sum().reindex(H, fill_value=0))
    return sum(frames) / len(frames)


def od_profile(files):
    """Hourly share of the demand injected in the archived runs (sum of creation rates)."""
    import json as js
    prof = np.zeros(24)
    for f in files:
        cfg = js.load(open(f.with_name(f.name.split("_uniq_")[0] + ".json")))
        tot = None
        for src in cfg["sources"].values():
            r = np.asarray(src["creation_rate"][:96], dtype=float)
            tot = r if tot is None else tot + r
        prof += tot.reshape(24, 4).sum(axis=1)
    return prof / prof.sum()


def mts_profile_2020(days):
    """Mean normalised hourly profile of coils with complete data on every validation day."""
    c = pd.read_csv(COILS_2020, sep=";", index_col=0)
    c.index = pd.to_datetime(c.index, utc=True).tz_convert("Europe/Rome").tz_localize(None)
    c = c[np.isin(c.index.date, days)]
    complete = c.columns[c.notna().all()]
    c = c[complete]
    hourly = c.groupby(c.index.hour).sum().reindex(H)
    keep = hourly.sum() > 0
    shares = hourly.loc[:, keep] / hourly.loc[:, keep].sum()
    return shares.mean(axis=1).values, int(keep.sum())


def mts_profile_ave(days):
    """Season-specific weekday averages (2022 table) for the 2021 week (times already local)."""
    a = pd.read_csv(COILS_AVE, sep=";")
    a = a[a.season == "summer"]
    cols = [x for x in a.columns if x.endswith("_0") or x.endswith("_1")]
    prof, n = [], None
    for d in days:
        wd = int(pd.Timestamp(d).strftime("%w"))
        s = a[a.wday_n == wd].copy()
        s["h"] = pd.to_datetime(str(d) + " " + s.time).dt.hour.values
        hourly = s.groupby("h")[cols].sum().reindex(H)
        keep = hourly.notna().all() & (hourly.sum() > 0)
        n = int(keep.sum())
        prof.append((hourly.loc[:, keep] / hourly.loc[:, keep].sum()).mean(axis=1).values)
    return np.mean(prof, axis=0), n


def link_metrics(sim, gps, n_days, shift=0):
    common = sim.columns.intersection(gps.columns)
    s = sim[common].astype(float)
    g = gps[common].astype(float)
    ok = (s.sum() > 0) & (g.sum() > 0)
    s, g = s.loc[:, ok], g.loc[:, ok]
    ps = s / s.sum()
    if shift:
        ps = pd.DataFrame(np.roll(ps.values, shift, axis=0), index=ps.index, columns=ps.columns)
    pg = g / g.sum()
    diff = (ps - pg).abs()
    m = pd.DataFrame({
        "cid": s.columns,
        "sim_daily": s.sum().values,
        "gps_total": g.sum().values,
        "eta": (g.sum() / (n_days * s.sum())).values,
        "eta_archived": (g.sum() / s.sum()).values,
        "mae_pp": 100 * diff.mean().values,
        "rmse_pp": 100 * np.sqrt((diff ** 2).mean()).values,
        "eps_rel": diff.sum().values,
        "pearson": [np.corrcoef(ps[c], pg[c])[0, 1] for c in s.columns],
    })
    m["log_eta"] = np.log10(m.eta)
    m["eta_class"] = np.rint(m.log_eta).astype(int)
    return m, ps, pg, len(common)


def baseline_mae(base, pg):
    return 100 * (pg.sub(base, axis=0)).abs().mean()


def q(x):
    x = np.asarray(x)
    return {k: float(np.percentile(x, p)) for k, p in
            [("p10", 10), ("p25", 25), ("median", 50), ("p75", 75), ("p90", 90)]} | {"n": int(len(x))}


def main():
    summary = {}
    metrics_by_year = {}
    for year, cfg in YEARS.items():
        gps, days, n_wd = load_viasat(cfg["viasat"])
        files = sim_files(cfg["sim"], cfg["exclude"])
        raw_files = sim_files(cfg["sim"], cfg["exclude"], corrected=False)
        sim = load_sim(files)
        sim_raw = load_sim(raw_files)
        sim_wd = sum(pd.Timestamp("20" + f.name.split("_uniq_")[1][:6]).dayofweek < 5 for f in files)
        m, ps, pg, n_common = link_metrics(sim, gps, len(days))
        m_shift, *_ = link_metrics(sim, gps, len(days), shift=1)
        m_raw, *_ = link_metrics(sim_raw, gps, len(days))
        m["mae_pp_shift1"] = m_shift.set_index("cid").loc[m.cid, "mae_pp"].values
        m["mae_pp_raw"] = m_raw.set_index("cid").reindex(m.cid)["mae_pp"].values
        od = od_profile(files)
        m["mae_pp_od"] = baseline_mae(od, pg).loc[m.cid].values
        if year == 2020:
            mts, n_coils = mts_profile_2020(days)
        else:
            mts, n_coils = mts_profile_ave(days)
        m["mae_pp_mts"] = baseline_mae(mts, pg).loc[m.cid].values
        m["year"] = year
        m.to_csv(OUT / f"link_metrics_{year}.csv", index=False)
        metrics_by_year[year] = (m, ps, pg)

        aggregate_sim = sim[m.cid].sum(axis=1)
        aggregate_gps = gps[m.cid].sum(axis=1)
        aggregate_mae = 100 * np.abs(aggregate_sim / aggregate_sim.sum() - aggregate_gps / aggregate_gps.sum()).mean()
        summary[str(year)] = {
            "viasat_days": [str(d) for d in days], "viasat_weekdays": n_wd,
            "sim_days": len(files), "sim_weekdays": int(sim_wd),
            "viasat_links": int(gps.shape[1]), "common_links": int(n_common), "usable_links": int(len(m)),
            "eta_median": float(m.eta.median()), "eta_archived_median": float(m.eta_archived.median()),
            "class_shares": {int(k): float(v) for k, v in m.eta_class.value_counts(normalize=True).sort_index().items()},
            "class_counts": {int(k): int(v) for k, v in m.eta_class.value_counts().sort_index().items()},
            "mae_pp": q(m.mae_pp), "eps_rel": q(m.eps_rel), "pearson": q(m.pearson), "rmse_pp": q(m.rmse_pp),
            "mae_pp_shift1": q(m.mae_pp_shift1), "mae_pp_raw": q(m.mae_pp_raw.dropna()),
            "mae_pp_od": q(m.mae_pp_od), "mae_pp_mts": q(m.mae_pp_mts), "mts_coils": n_coils,
            "share_sim_better_than_od": float((m.mae_pp < m.mae_pp_od).mean()),
            "share_sim_better_than_mts": float((m.mae_pp < m.mae_pp_mts).mean()),
            "aggregate_mae_pp": float(aggregate_mae),
            "peak_hour_sim": int(aggregate_sim.idxmax()), "peak_hour_gps": int(aggregate_gps.idxmax()),
            "by_class": {int(k): {"n": int(len(g)), "eta_median": float(g.eta.median()),
                                  "mae_pp": q(g.mae_pp), "eps_rel": q(g.eps_rel), "pearson_median": float(g.pearson.median()),
                                  "mae_pp_od_median": float(g.mae_pp_od.median()), "mae_pp_mts_median": float(g.mae_pp_mts.median())}
                         for k, g in m.groupby("eta_class")},
            "probe_ge_100": {"n": int((m.gps_total >= 100).sum()), "mae_pp": q(m.loc[m.gps_total >= 100, "mae_pp"])},
        }

    # ---------------- Figure: CDF of the profile error by penetration class ----------------
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.9), sharey=True, constrained_layout=True)
    for ax, (year, (m, _, _)) in zip(axes, metrics_by_year.items()):
        for k in sorted(m.eta_class.unique(), reverse=True):
            g = np.sort(m.loc[m.eta_class == k, "eps_rel"].values * 100)
            if len(g) < 5:
                continue
            ax.step(g, np.arange(1, len(g) + 1) / len(g), where="post", color=CLASS_COLORS.get(k, "#999"),
                    lw=1.8, label=rf"$\eta\sim10^{{{k}}}$ ({len(g)})")
        for col, ls, lab in [("mae_pp_od", ":", "OD profile"), ("mae_pp_mts", "--", "MTS mean profile")]:
            g = np.sort(m[col].values * 24)
            ax.step(g, np.arange(1, len(g) + 1) / len(g), where="post", color="#8D8D8D", ls=ls, lw=1.5,
                    label=f"{lab}, all links")
        ax.set_xlabel(r"Relative profile error $\varepsilon_i$ (%)")
        ax.set_title(f"{year}", loc="left")
        ax.set_xlim(0, 100)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8.5, loc="lower right")
    axes[0].set_ylabel("Cumulative fraction of links")
    save(fig, "10_validation_cdf")

    # ---------------- Penetration panels with the corrected eta ----------------
    roads = gpd.read_file(CARTO).to_crs(3857)
    for year, (m, _, _) in metrics_by_year.items():
        counts = m.eta_class.value_counts().sort_index(ascending=False)
        fig, ax = plt.subplots(figsize=(5.2, 4.2), constrained_layout=True)
        ax.bar([rf"$10^{{{k}}}$" for k in counts.index], 100 * counts.values / counts.sum(),
               color=[CLASS_COLORS.get(k, "#999") for k in counts.index])
        for i, v in enumerate(100 * counts.values / counts.sum()):
            ax.text(i, v + 1, f"{v:.1f}%", ha="center", fontsize=10)
        ax.set_xlabel(r"Penetration class $\eta$")
        ax.set_ylabel("Share of links (%)")
        save(fig, f"6b_penetration_statistics_{year}")

        gm = roads.merge(m[["cid", "eta_class"]], left_on="poly_cid", right_on="cid")
        fig, ax = plt.subplots(figsize=(6.5, 5.2), constrained_layout=True)
        xmin, ymin, xmax, ymax = gm.total_bounds
        pad = 0.08 * max(xmax - xmin, ymax - ymin)
        roads.cx[xmin - pad:xmax + pad, ymin - pad:ymax + pad].plot(ax=ax, color="#CFCFCF", lw=0.3, zorder=1)
        for k in sorted(gm.eta_class.unique()):
            gm[gm.eta_class == k].plot(ax=ax, color=CLASS_COLORS.get(k, "#999"), lw=1.4, zorder=3 + k + 5)
        ax.set_xlim(xmin - pad, xmax + pad); ax.set_ylim(ymin - pad, ymax + pad)
        ax.legend(handles=[Line2D([0], [0], color=CLASS_COLORS.get(k, "#999"), lw=3, label=rf"$\eta\sim10^{{{k}}}$")
                           for k in sorted(gm.eta_class.unique(), reverse=True)], loc="lower right", fontsize=9)
        ax.set_axis_off()
        save(fig, f"6c_cluster_{year}")

    # ---------------- Normalised Ward clustering of the 2020 candidate set ----------------
    m, ps, pg = metrics_by_year[2020]
    gps2020, days2020, _ = load_viasat(YEARS[2020]["viasat"])
    sim2020 = load_sim(sim_files(YEARS[2020]["sim"], []))
    ic = pd.read_csv(INNER_CLUSTER, sep=";")
    cand = [c for c in ic.cid if c in ps.columns]
    shares = ps[cand].T.values  # rows = links, columns = hours, each row sums to 1
    Z = sch.linkage(shares, method="ward", metric="euclidean")
    labels = sch.fcluster(Z, 3, criterion="maxclust") - 1
    cut = 0.5 * (Z[-3, 2] + Z[-2, 2])
    # raw-count clustering (archived) for comparison
    Z_raw = sch.linkage(sim2020[cand].T.values, method="ward", metric="euclidean")
    labels_raw = sch.fcluster(Z_raw, 3, criterion="maxclust") - 1
    from sklearn.metrics import adjusted_rand_score
    ari = adjusted_rand_score(labels_raw, labels)
    old_labels = ic.set_index("cid").loc[cand, "cluster"].values
    ari_archived = adjusted_rand_score(old_labels, labels)
    # order clusters by size of the morning peak share, so that colours are stable
    order = np.argsort([shares[labels == k][:, 6:9].sum(axis=1).mean() for k in range(3)])[::-1]
    relabel = {int(old): new for new, old in enumerate(order)}
    labels = np.array([relabel[int(x)] for x in labels])
    cl = pd.DataFrame({"cid": cand, "cluster": labels})
    gdf = gpd.GeoDataFrame(ic.assign(geometry=gpd.GeoSeries.from_wkt(ic.geometry)), crs=4326)
    gdf = gdf.drop(columns="cluster").merge(cl, on="cid").to_crs(3857)
    gdf["x"] = gdf.geometry.interpolate(0.5, normalized=True).x
    gdf["y"] = gdf.geometry.interpolate(0.5, normalized=True).y
    met = m.set_index("cid")
    gdf = gdf.join(met[["mae_pp", "eps_rel", "sim_daily", "gps_total", "eta"]], on="cid")
    elig = gdf[(gdf.sim_daily >= 300) & (gdf.gps_total >= 50)]
    fixed = elig[elig.cid == FIXED_REPRESENTATIVE]
    if len(fixed) != 1:
        raise ValueError("fixed representative not eligible")
    kf = int(fixed.cluster.iloc[0])
    pools = [fixed.to_dict("records") if k == kf else elig[elig.cluster == k].to_dict("records") for k in range(3)]
    best = None
    for sel in itertools.product(*pools):
        d = [np.hypot(a["x"] - b["x"], a["y"] - b["y"]) / 1000 for a, b in itertools.combinations(sel, 2)]
        if min(d) < MIN_SEPARATION_KM:
            continue
        score = sum(s["mae_pp"] for s in sel)
        if best is None or score < best[0]:
            best = (score, sel, min(d))
    reps = pd.DataFrame([{"cluster": int(s["cluster"]), "cid": int(s["cid"]), "mae_pp": s["mae_pp"],
                          "eps_rel": s["eps_rel"], "eta": s["eta"],
                          "mae_pp_rank_pct": float((m.mae_pp < s["mae_pp"]).mean() * 100)} for s in best[1]])
    reps.to_csv(OUT / "representatives_2020.csv", index=False)
    summary["clustering_2020"] = {
        "candidate_links": len(cand), "cluster_sizes": {int(k): int(v) for k, v in cl.cluster.value_counts().sort_index().items()},
        "cut_distance": float(cut), "ari_vs_raw_count_ward": float(ari), "ari_vs_archived_clusters": float(ari_archived),
        "eligible_links": int(len(elig)), "min_separation_km": float(best[2]),
        "representatives": reps.to_dict("records"),
        "candidate_mae_pp": q(gdf.mae_pp.dropna()),
    }

    # dendrogram
    fig, ax = plt.subplots(figsize=(6.8, 3.7), constrained_layout=True)
    n = len(cand)
    leaves = {i: [i] for i in range(n)}
    for i, row in enumerate(Z):
        leaves[n + i] = leaves[int(row[0])] + leaves[int(row[1])]

    def col(node):
        ks = {labels[i] for i in leaves[node]}
        return SUB_COLORS[ks.pop()] if len(ks) == 1 else "#9A9A9A"
    sch.dendrogram(Z, no_labels=True, link_color_func=col, ax=ax)
    ax.axhline(cut, color="#545454", ls="--", lw=1.1, label="Three-cluster cut")
    ax.set_xlabel(f"Polylines ({n})")
    ax.set_ylabel("Ward distance (hourly shares)")
    ax.legend(loc="upper right", fontsize=9)
    save(fig, "7a_dendrogram")

    fig, ax = plt.subplots(figsize=(6.4, 5.2), constrained_layout=True)
    for k, g in gdf.groupby("cluster"):
        g.plot(ax=ax, color=SUB_COLORS[int(k)], lw=1.8, label=f"Subcluster {int(k) + 1} ({len(g)})")
    ax.set_axis_off()
    ax.legend(loc="lower left", fontsize=9)
    save(fig, "7b_dendrogram_geoloc")

    # mean share profile of each subcluster (supplementary)
    fig, ax = plt.subplots(figsize=(6.4, 3.6), constrained_layout=True)
    for k in range(3):
        ax.plot(H, 100 * shares[labels == k].mean(axis=0), color=SUB_COLORS[k], lw=2, label=f"Subcluster {k + 1}")
    ax.set_xlabel("Hour of day"); ax.set_ylabel("Mean hourly share (%)")
    ax.set_xticks(range(0, 24, 3)); ax.legend(fontsize=9); ax.grid(alpha=0.3)
    save(fig, "S_subcluster_profiles")

    # representative panels
    stems = {0: "8a_cluster_black", 1: "8c_cluster_red", 2: "8b_cluster_blue"}
    for r in reps.itertuples():
        s = sim2020[r.cid].astype(float)
        g = gps2020[r.cid].astype(float)
        scaled = g * s.sum() / g.sum()
        err = 100 * np.abs(s / s.sum() - g / g.sum())
        fig, (a1, a2) = plt.subplots(2, 1, figsize=(6.5, 4.7), sharex=True,
                                     gridspec_kw={"height_ratios": [1.75, 1]}, constrained_layout=True)
        c = SUB_COLORS[r.cluster]
        a1.plot(H, s, color=c, lw=2, label="Simulation")
        a1.plot(H, scaled, color="#6E6E6E", ls=(0, (4, 2)), lw=2, label="Viasat, penetration-normalized")
        a1.set_ylabel(r"$\Phi$ (veh/h)")
        a1.set_title(f"Subcluster {r.cluster + 1} | polyline {r.cid}", loc="left", fontsize=11)
        a1.legend(loc="upper left", fontsize=9, frameon=False)
        a2.bar(H, err, color=c, alpha=0.85, width=0.62)
        a2.axhline(err.mean(), color="#333", ls="--", lw=1.1)
        a2.text(0.98, 0.92, f"MAE = {err.mean():.2f} pp ($\\varepsilon$ = {100 * r.eps_rel:.0f}%)",
                transform=a2.transAxes, ha="right", va="top", fontsize=9,
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#DDD"))
        a2.set_ylabel("|Δ share| (pp)")
        a2.set_xlabel("Hour of day")
        a2.set_xticks(range(0, 24, 3)); a2.set_xticklabels([f"{h:02d}:00" for h in range(0, 24, 3)], rotation=45)
        save(fig, stems[r.cluster])

    rep_map = gdf[gdf.cid.isin(reps.cid)]
    fig, ax = plt.subplots(figsize=(6.0, 5.6), constrained_layout=True)
    xmin, ymin, xmax, ymax = rep_map.total_bounds
    b = 9000
    roads.cx[xmin - b:xmax + b, ymin - b:ymax + b].plot(ax=ax, color="#CBCBCB", lw=0.6, zorder=2)
    ax.set_xlim(xmin - b, xmax + b); ax.set_ylim(ymin - b, ymax + b)
    for row in rep_map.itertuples():
        gpd.GeoSeries([row.geometry], crs=rep_map.crs).plot(ax=ax, color="white", lw=7, zorder=4)
        gpd.GeoSeries([row.geometry], crs=rep_map.crs).plot(ax=ax, color=SUB_COLORS[row.cluster], lw=4.5, zorder=5)
        mp = row.geometry.interpolate(0.5, normalized=True)
        ax.annotate(f"Polyline {row.cid}", xy=(mp.x, mp.y), xytext=(8, 10), textcoords="offset points",
                    fontsize=9, fontweight="bold", color=SUB_COLORS[row.cluster],
                    bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#DDD"), zorder=6)
    ax.set_axis_off()
    save(fig, "8d_representative_polylines_location")

    (OUT / "validation_summary.json").write_text(json.dumps(summary, indent=2, default=float))
    print(json.dumps(summary, indent=1, default=float)[:6000])


if __name__ == "__main__":
    main()
