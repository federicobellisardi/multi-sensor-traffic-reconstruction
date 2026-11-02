#!/usr/bin/env python3
"""Assimilation, GPS validation and leave-one-detector-out test for the corrected reconstruction.

Pipeline (run from the repository root after the final simulations):
  1. assimilate every simulated day with analysis/correction_fixed.py and the observed MTS
     coil tables (UTC, converted to local time inside the correction);
  2. compare hourly shares with the Viasat GPS extracts on all usable matched links, with
     three baselines (injected OD profile, mean MTS profile of the same days, uniform);
  3. leave-one-detector-out: every coil with complete local-day data is removed from the
     assimilation in turn and its observed hourly counts are compared with the raw and the
     assimilated reconstruction on its link.

Usage: python3 model/analysis/reconstruct_and_validate.py [assimilate|validate|loo|all]
Outputs: model/results/corrected/ (aggregate), model/results/private/ (link level, ignored).
"""
import contextlib
import io
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from paths import ROOT, RESULTS as R1, SIM_RUNS  # noqa: E402
SIM = Path(os.environ.get("SIM_DIR", SIM_RUNS / "demand/V6_scaled"))  # final configuration (demand_scaling.py)
COILS = Path(os.environ.get("COIL_DIR", SIM_RUNS / "coils"))
OUT = Path(os.environ.get("OUT_DIR", R1 / "corrected"))
PRIV = Path(os.environ.get("PRIV_DIR", R1 / "private"))  # per-link tables (proprietary-derived)
H = pd.Index(range(24), name="hour")
CAMPAIGNS = {2020: "viasat_20200210_20200218_timed_fluxes.csv",
             2021: "viasat_20210628_20210705_timed_fluxes.csv"}
COIL_TABLES = {2020: ROOT / "data/old_coils_data/_coils_table_200201-000000_200331-234500.csv"}

from correction_fixed import SimPostCorrection  # noqa: E402


def basenames():
    return sorted(str(p).split("_uniq_")[0] for p in SIM.glob("sim_*_uniq_*_000000.csv"))


def prepare_coils():
    COILS.mkdir(parents=True, exist_ok=True)
    dst = COILS / COIL_TABLES[2020].name.lstrip("_")
    if not dst.exists():
        dst.symlink_to(COIL_TABLES[2020])
    for f in list((ROOT / "data").glob("coils_std_*.csv")) + list((ROOT / "data").glob("coils_ave_*.csv")):
        if not (COILS / f.name).exists():
            (COILS / f.name).symlink_to(f)


def corrector(base):
    with contextlib.redirect_stdout(io.StringIO()):
        return SimPostCorrection({"coils_table_dir": str(COILS)}, base)


def assimilate_one(base):
    sim = corrector(base)
    with contextlib.redirect_stdout(io.StringIO()):
        f = sim.correct([])
    return base, f


# ---------------------------------------------------------------- validation
def load_sim(path):
    d = pd.read_csv(path, sep=";")
    cols = [c for c in d if c.startswith("20")]
    assert len(cols) == 24 and len(set(pd.to_datetime(cols).hour)) == 24, path
    assert not d.duplicated(["poly_cid", "oneway"]).any(), path
    s = d.groupby("poly_cid")[cols].sum().T
    s.index = pd.to_datetime(s.index).hour
    return s.reindex(H).astype(float)


def od_profile(base):
    c = json.load(open(base + ".json"))
    r = np.sum([np.asarray(s["creation_rate"][:96], float) for s in c["sources"].values()], axis=0)
    return r.reshape(24, 4).sum(axis=1)


def coil_table_local(year):
    f = sorted(COILS.glob(f"coils_table_{str(year)[2:]}*.csv"))[0]
    d = pd.read_csv(f, sep=";", index_col=0)
    d.index = pd.to_datetime(d.index, utc=True).tz_convert("Europe/Rome").tz_localize(None)
    return d


def mts_profile(year, days):
    d = coil_table_local(year)
    d = d[np.isin(d.index.date, days)]
    expected = pd.DatetimeIndex([pd.Timestamp(day) + pd.Timedelta(minutes=15 * k) for day in days for k in range(96)])
    d = d.reindex(expected)
    d = d.loc[:, d.notna().all() & (d.sum() > 0)]
    h = d.groupby(d.index.hour).sum().reindex(H)
    return (h / h.sum()).mean(axis=1).values, d.shape[1]


def quant(a):
    a = np.asarray(a, float)
    a = a[np.isfinite(a)]
    return dict(n=int(len(a)), **{k: float(np.percentile(a, q)) for k, q in
                                  [("p10", 10), ("p25", 25), ("median", 50), ("p75", 75), ("p90", 90)]})


def metrics(s, g, od, mts):
    common = s.columns.intersection(g.columns)
    common = common[(s[common].sum() > 0) & (g[common].sum() > 0)]
    ps, pg = s[common] / s[common].sum(), g[common] / g[common].sum()
    mae = lambda pred: 100 * pg.sub(pred, axis=0).abs().mean()  # noqa: E731
    m = pd.DataFrame({"mae_pp": 100 * (ps - pg).abs().mean(), "pearson": ps.corrwith(pg),
                      "gps_total": g[common].sum(), "sim_total": s[common].sum()})
    m.index.name = "cid"
    m["mae_pp_od"] = mae(od / od.sum())
    m["mae_pp_mts"] = mae(mts)
    m["mae_pp_flat"] = mae(np.ones(24) / 24)
    return m


def unchanged_gps_links():
    """GPS link counts were map-matched on the 2023 graph; keep links whose geometry is identical
    (Hausdorff distance <= 1 m) in the project cartography used here."""
    f = R1 / "private" / "gps_links_unchanged.csv"  # property of the cartography, shared by all runs
    if not f.exists():
        import geopandas as gpd
        new = gpd.read_file(R1 / "carto_a059fb0.geojson").to_crs(32632).set_index("poly_cid")
        old = gpd.read_file(ROOT / "article/data/uniq/carto.geojson").to_crs(32632).set_index("poly_cid")
        c = new.index.intersection(old.index)
        h = pd.Series([new.geometry[i].hausdorff_distance(old.geometry[i]) for i in c], index=c, name="hausdorff_m")
        h.to_csv(f)
    h = pd.read_csv(f, index_col=0).hausdorff_m
    return set(h[h <= 1.0].index)


def validate():
    PRIV.mkdir(parents=True, exist_ok=True)
    keep = unchanged_gps_links()
    summary = {}
    for year, gname in CAMPAIGNS.items():
        v = pd.read_csv(ROOT / "work_viasat" / gname, sep=";", parse_dates=["time"])
        n_gps_links = int((v.groupby("cid").total_fluxes.sum() > 0).sum())
        v = v[v.cid.isin(keep)]
        days = sorted(v.time.dt.date.unique())
        gday = {d: v[v.time.dt.date == d].groupby([v.time.dt.hour, "cid"]).total_fluxes.sum()
                .unstack(fill_value=0).reindex(H, fill_value=0) for d in days}
        sim, raw, od = {}, {}, {}
        for d in days:
            base = str(SIM / f"sim_{pd.Timestamp(d):%y%m%d}")
            rawf = Path(f"{base}_uniq_{pd.Timestamp(d):%y%m%d}_000000.csv")
            sim[d], raw[d], od[d] = load_sim(str(rawf) + ".corrected"), load_sim(rawf), od_profile(base)
        camp = {"days": [str(d) for d in days], "day_types": {}, "gps_links_original_graph": n_gps_links}
        for kind in ["all", "weekday", "weekend"]:
            sel = [d for d in days if kind == "all" or (pd.Timestamp(d).dayofweek < 5) == (kind == "weekday")]
            s, g, o = sum(sim[d] for d in sel), sum(gday[d] for d in sel), sum(od[d] for d in sel)
            mts, ncoil = mts_profile(year, sel)
            m = metrics(s, g, o, mts)
            m["mae_pp_raw"] = metrics(sum(raw[d] for d in sel), g, o, mts).mae_pp.reindex(m.index)
            m.to_csv(PRIV / f"corrected_link_metrics_{year}_{kind}.csv")
            st = {"days": len(sel), "links": len(m), "mts_directions": ncoil,
                  **{c: quant(m[c]) for c in ["mae_pp", "mae_pp_raw", "pearson", "mae_pp_od", "mae_pp_mts", "mae_pp_flat"]},
                  "share_better_od": float((m.mae_pp < m.mae_pp_od).mean()),
                  "share_better_mts": float((m.mae_pp < m.mae_pp_mts).mean()),
                  "median_paired_gain_od_pp": float((m.mae_pp_od - m.mae_pp).median()),
                  "median_paired_gain_mts_pp": float((m.mae_pp_mts - m.mae_pp).median())}
            camp["day_types"][kind] = st
            if kind == "all":
                agg_s, agg_g = s[m.index].sum(axis=1), g[m.index].sum(axis=1)
                pd.DataFrame({"hour": range(24), "sim_share": agg_s / agg_s.sum(), "gps_share": agg_g / agg_g.sum(),
                              "mts_share": mts, "od_share": o / o.sum()}).to_csv(OUT / f"aggregate_profiles_{year}.csv", index=False)
                camp["aggregate_peak_hour_sim"] = int(agg_s.idxmax())
                camp["aggregate_peak_hour_gps"] = int(agg_g.idxmax())
                camp["aggregate_profile_mae_pp"] = float(100 * (agg_s / agg_s.sum() - agg_g / agg_g.sum()).abs().mean())
                lag = {}
                for k in (-1, 0, 1):
                    lag[k] = float(100 * (np.roll(agg_s / agg_s.sum(), k) - agg_g / agg_g.sum()).abs().mean())
                camp["aggregate_profile_mae_by_shift_pp"] = lag
                strata = {}
                for name, mask in [("1-49", m.gps_total < 50), ("50-199", m.gps_total.between(50, 199)),
                                   ("200+", m.gps_total >= 200)]:
                    strata[name] = {"links": int(mask.sum()), "mae_pp": quant(m.mae_pp[mask])["median"],
                                    "mae_pp_mts": quant(m.mae_pp_mts[mask])["median"],
                                    "pearson": quant(m.pearson[mask])["median"]}
                camp["probe_strata"] = strata
        summary[str(year)] = camp
        print(year, json.dumps({k: camp["day_types"]["all"][k]["median"] for k in
                                ["mae_pp", "mae_pp_raw", "mae_pp_od", "mae_pp_mts", "pearson"]}), flush=True)
    (OUT / "validation_summary.json").write_text(json.dumps(summary, indent=2) + "\n")


# ---------------------------------------------------------------- leave-one-out
def loo_one(base):
    sim = corrector(base)
    raw = pd.read_csv(sim.unique_file, sep=";")
    cols = [c for c in raw.columns if c.startswith("20")]
    day = pd.to_datetime(cols[0]).normalize()
    year = day.year
    obs = coil_table_local(year)
    obs = obs[(obs.index >= day) & (obs.index < day + pd.Timedelta(days=1))]
    mapped = sorted(set(int(c.split("_")[0]) for c in sim.dfc.columns))
    complete = [c for c in mapped if all(f"{c}_{k}" in obs.columns for k in (0, 1))
                and len(obs) == 96 and obs[[f"{c}_0", f"{c}_1"]].notna().all().all()]
    base_p2c, tags = dict(sim.poly2coil), list(sim.dfb.tag.values)

    def run(pcid):
        # every coil on the held-out link is removed (co-located detectors would leak its count)
        sim.poly2coil = {k: v for k, v in base_p2c.items() if k != pcid}
        with contextlib.redirect_stdout(io.StringIO()):
            f = sim.correct([t for t in tags if sim.coil2poly[t] != pcid], suffix="loo")
        return pd.read_csv(f, sep=";")

    rows = []
    for c in complete:
        pcid = sim.coil2poly[c]
        loo = run(pcid)
        for dcarto, ow in [("IN", "FT"), ("OUT", "TF")]:
            key = f"{c}_{dcarto}"
            if key not in sim.dfc.columns:
                continue
            o = sim.dfc[key].resample("1h").sum().values.astype(float) if len(sim.dfc) > 24 else sim.dfc[key].values.astype(float)
            r = raw[(raw.poly_cid == pcid) & (raw.oneway == ow)][cols].values.ravel().astype(float)
            a = loo[(loo.poly_cid == pcid) & (loo.oneway == ow)][cols].values.ravel().astype(float)
            rows.append(dict(day=str(day.date()), coil=c, poly_cid=pcid, direction=dcarto,
                             present_raw=len(r) == 24, present_loo=len(a) == 24,
                             obs_total=o.sum(), raw_total=r.sum() if len(r) == 24 else np.nan,
                             loo_total=a.sum() if len(a) == 24 else np.nan,
                             raw_abs=np.abs(r - o).sum() if len(r) == 24 else np.nan,
                             loo_abs=np.abs(a - o).sum() if len(a) == 24 else np.nan,
                             changed=bool(len(a) == 24 and len(r) == 24 and np.any(np.abs(a - r) > 0.5))))
    sim.poly2coil = base_p2c
    return rows


def loo():
    with ProcessPoolExecutor(int(os.environ.get("NPROC", 6))) as ex:
        rows = [r for rs in ex.map(loo_one, basenames()) for r in rs]
    d = pd.DataFrame(rows)
    d.to_csv(OUT / "loo_detectors.csv", index=False)
    rep = {}
    for year, z in d.groupby(d.day.str[:4]):
        by = z.groupby("coil")[["obs_total", "raw_abs", "loo_abs"]].sum()
        nd = z.groupby("coil").day.nunique()  # detectors have different numbers of valid days: compare mean daily volumes
        a = by.to_numpy()
        rng = np.random.default_rng(20261027)
        boot = [100 * (s[1] - s[2]) / s[0] for s in (a[rng.integers(0, len(a), len(a))].sum(axis=0) for _ in range(5000))]
        rep[year] = {"coils": int(z.coil.nunique()), "coil_days": int(z.groupby(["coil", "day"]).ngroups),
                     "directional_records": int(len(z)), "missing_directions": int((~z.present_loo).sum()),
                     "pooled_raw_error_pct": float(100 * z.raw_abs.sum() / z.obs_total.sum()),
                     "pooled_loo_error_pct": float(100 * z.loo_abs.sum() / z.obs_total.sum()),
                     "pooled_reduction_pp": float(100 * (z.raw_abs.sum() - z.loo_abs.sum()) / z.obs_total.sum()),
                     "bootstrap95_reduction_pp": np.percentile(boot, [2.5, 97.5]).tolist(),
                     "median_coil_raw_pct": float((100 * by.raw_abs / by.obs_total).median()),
                     "median_coil_loo_pct": float((100 * by.loo_abs / by.obs_total).median()),
                     "share_reached": float(z.groupby("coil").changed.any().mean()),
                     "share_improved": float(((by.loo_abs < by.raw_abs - 1e-9)).mean()),
                     "share_worse": float(((by.loo_abs > by.raw_abs + 1e-9)).mean()),
                     "raw_to_observed_volume_ratio": float(z.raw_total.sum() / z.obs_total.sum()),
                     "log_volume_ratio_median": float(np.median(np.log10(by.assign(r=z.groupby("coil").raw_total.sum()).r / by.obs_total))),
                     "volume_spearman": float((z.groupby("coil").raw_total.sum() / nd).corr(by.obs_total / nd, method="spearman")),
                     "loo_volume_spearman": float((z.groupby("coil").loo_total.sum() / nd).corr(by.obs_total / nd, method="spearman")),
                     "loo_to_observed_volume_ratio": float(z.loo_total.sum() / z.obs_total.sum()),
                     "median_abs_log10_ratio_raw": float(np.median(np.abs(np.log10(z.groupby("coil").raw_total.sum().clip(lower=1) / by.obs_total)))),
                     "median_abs_log10_ratio_loo": float(np.median(np.abs(np.log10(z.groupby("coil").loo_total.sum().clip(lower=1) / by.obs_total))))}
    (OUT / "loo_summary.json").write_text(json.dumps(rep, indent=2) + "\n")
    print(json.dumps(rep, indent=1))


def main():
    step = sys.argv[1] if len(sys.argv) > 1 else "all"
    OUT.mkdir(parents=True, exist_ok=True)
    prepare_coils()
    if step in ("assimilate", "all"):
        with ProcessPoolExecutor(int(os.environ.get("NPROC", 6))) as ex:
            for b, f in ex.map(assimilate_one, basenames()):
                print("assimilated", Path(f).name, flush=True)
    if step in ("validate", "all"):
        validate()
    if step in ("loo", "all"):
        loo()


if __name__ == "__main__":
    main()
