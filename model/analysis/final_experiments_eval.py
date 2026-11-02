#!/usr/bin/env python3
"""Evaluation of the experiments on the frozen model. Rules: model/results/experiments/PROTOCOL.md.

  python3 final_experiments_eval.py e1|e2|e3k|e3f|e3c|e4|e5|e6|e7|e8 -> model/results/experiments/<name>.json
"""
import contextlib
import io
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calibrate_demand as C  # noqa: E402
import demand_scaling as D  # noqa: E402
import direction_diagnosis as DD  # noqa: E402
import final_experiments as F  # noqa: E402
import gps_validation_split as G  # noqa: E402
import od_factor_decomposition as OD  # noqa: E402
import od_matrix as M  # noqa: E402
import province_demand as PD  # noqa: E402
import reconstruct_and_validate as P  # noqa: E402
import radius_scan as S  # noqa: E402
import source_value as V  # noqa: E402
from paths import ROOT, RESULTS as R1  # noqa: E402

RES = R1 / "experiments"
N_BOOT, SEED = 2000, 20261051
MON, SAT = C.CAL_DAYS
MODEL = D.OUT / "V6_scaled"
MAR = {MON: ["2020-03-16", "2020-03-17", "2020-03-18", "2020-03-19", "2020-03-20", "2020-03-23", "2020-03-24", "2020-03-25", "2020-03-26", "2020-03-27"], SAT: ["2020-03-21", "2020-03-22", "2020-03-28"]}
MIN_DAYS = {MON: 2, SAT: 1}
ci = lambda v: [float(x) for x in np.percentile(v, [2.5, 97.5])]
out_of = lambda name: F.OUT / name


def save(name, res):
    RES.mkdir(parents=True, exist_ok=True)
    (RES / f"{name}.json").write_text(json.dumps(res, indent=1, default=float) + "\n")
    print(json.dumps(res, indent=1, default=float))


def table_obs():
    d = pd.read_csv(ROOT / "data/old_coils_data/_coils_table_200201-000000_200331-234500.csv", sep=";", index_col=0)
    d.index = pd.to_datetime(d.index, utc=True).tz_convert("Europe/Rome").tz_localize(None)
    return d


def day_volume(z):
    """Daily volume of one direction with isolated gaps read as zero, or NaN: at most 20 missing intervals, none longer than 4."""
    if len(z) != 96:
        return np.nan
    m = z.isna().values
    if m.sum() > 20:
        return np.nan
    run = best = 0
    for x in m:
        run = run + 1 if x else 0
        best = max(best, run)
    return float(z.sum()) if best <= 4 else np.nan


def mean_volume(obs, coil, days, need):
    v = []
    for day in days:
        z = obs[obs.index.strftime("%Y-%m-%d") == day]
        a, b = day_volume(z[f"{coil}_0"]), day_volume(z[f"{coil}_1"])
        if np.isfinite(a) and np.isfinite(b) and a + b > 0:
            v.append(a + b)
    return float(np.mean(v)) if len(v) >= need else np.nan


def agents(path, day):
    return sum(sum(s["creation_rate"]) for s in json.load(open(path / f"sim_{D.tag(day)}.json"))["sources"].values())


def e1():
    obs, rng, res = table_obs(), np.random.default_rng(SEED), {}
    bar = pd.read_csv(ROOT / "vars/extra/er_barriers_cartodata.csv", sep=";").drop_duplicates("tag").set_index("tag").poly_lid
    u = D.group_observations().drop_duplicates("coil").reset_index(drop=True)
    cal = set(u.coil[V.E.split(u)])
    known = set(u.coil)
    for day in (MON, SAT):
        rows = []
        for coil in sorted(c for c in bar.index if f"{c}_0" in obs and f"{c}_1" in obs):
            a, b = mean_volume(obs, coil, D.GROUPS[day][0], MIN_DAYS[day]), mean_volume(obs, coil, MAR[day], MIN_DAYS[day])
            if np.isfinite(a) and np.isfinite(b):
                rows.append((coil, bar[coil], a, b))
        t = pd.DataFrame(rows, columns=["coil", "poly_lid", "feb", "mar"])
        t["obs_change"] = t.mar / t.feb
        for n, p in (("feb_sim", MODEL), ("sim", out_of("ld")), ("sim_no_od", out_of("ld_no_od"))):
            t[n] = V.daily(p, day, t.poly_lid)
        t = t[(t.feb_sim > 0) & (t.sim > 0)]
        t["sim_change"], t["no_od_change"] = t.sim / t.feb_sim, t.sim_no_od.clip(lower=1) / V.daily(V.OUT / "no_od", day, t.poly_lid).clip(min=1)
        dem = agents(out_of("ld"), day) / agents(MODEL, day)
        det = float(t[t.coil.isin(cal)].obs_change.median())
        h = t[t.coil.isin(known) & ~t.coil.isin(cal)].reset_index(drop=True)
        h.assign(day=day)[["day", "coil", "obs_change", "sim_change", "no_od_change"]].to_csv(RES / f"e1_detectors_{D.tag(day)}.csv", index=False)
        err = lambda s: np.abs(np.log10(s / h.obs_change.values))
        e = {"sim": err(h.sim_change.values), "dem": err(np.full(len(h), dem)), "det": err(np.full(len(h), det)), "no_od": err(h.no_od_change.values)}
        idx = [rng.integers(0, len(h), len(h)) for _ in range(N_BOOT)]
        diff = lambda a, b: ci([np.median(e[a][i]) - np.median(e[b][i]) for i in idx])
        res[day] = {"test_detectors": len(h), "demand_change": dem, "calibration_median_change": det, "observed_median_change": float(h.obs_change.median()), "simulated_median_change": float(h.sim_change.median()),
                    "error": {k: float(np.median(v)) for k, v in e.items()}, "sim_minus_dem_ci95": diff("sim", "dem"), "sim_minus_det_ci95": diff("sim", "det"), "sim_minus_no_od_ci95": diff("sim", "no_od"),
                    "spearman_change_sim": float(spearmanr(h.sim_change, h.obs_change)[0]), "spearman_change_no_od": float(spearmanr(h.no_od_change, h.obs_change)[0]),
                    "spearman_change_sim_ci95": ci([spearmanr(h.sim_change.values[i], h.obs_change.values[i])[0] for i in idx]),
                    "spearman_level_march": float(spearmanr(h.sim, h.mar)[0]), "ratio_level_march": float(h.sim.sum() / h.mar.sum()), "median_abs_log_level_march": float(np.median(np.abs(np.log10(h.sim / h.mar))))}
    res["rule_met"] = any(res[d]["sim_minus_dem_ci95"][1] < 0 for d in (MON, SAT))
    save("e1_lockdown", res)


def e2():
    rng, res = np.random.default_rng(SEED + 2), {}
    arms = {"O1F1": lambda d: MODEL, "O1F0": M.frozen_path, "O0F1": lambda d: out_of("fact_no_od"), "O0F0": lambda d: F.no_relations_no_factors()}
    for day in (MON, SAT):
        res[day] = {}
        for name, t in V.sets(day).items():
            o = t.obs.values
            s = {k: V.daily(f(day), day, t.poly_lid) for k, f in arms.items()}
            x = {"relations_with_factors": OD.compare(s["O1F1"], s["O0F1"], o, rng), "factors_with_relations": OD.compare(s["O1F1"], s["O1F0"], o, rng),
                 "factors_without_relations": OD.compare(s["O0F1"], s["O0F0"], o, rng), "relations_without_factors": OD.compare(s["O1F0"], s["O0F0"], o, rng)}
            keep = np.where((s["O1F1"] > 0) & (s["O0F1"] > 0) & (s["O1F0"] > 0) & (s["O0F0"] > 0))[0]
            sd = lambda a, i: np.log10(s[a][i] / o[i]).std()
            sp = lambda a, i: spearmanr(o[i], s[a][i])[0]
            I1 = [sd("O1F1", i) - sd("O0F1", i) - sd("O1F0", i) + sd("O0F0", i) for i in (rng.choice(keep, len(keep)) for _ in range(N_BOOT))]
            I2 = [sp("O1F1", i) - sp("O0F1", i) - sp("O1F0", i) + sp("O0F0", i) for i in (rng.integers(0, len(o), len(o)) for _ in range(N_BOOT))]
            x["interaction_sd_ci95"], x["interaction_spearman_ci95"] = ci(I1), ci(I2)
            res[day][name] = x
    rr = [res[d][n]["relations_with_factors"] for d in (MON, SAT) for n in res[d]]
    res["rule_met_in"] = sum(x["spearman_diff_ci95"][0] > 0 or x["sd_diff_ci95"][1] < 0 for x in rr)
    save("e2_factorial", res)


def e3k():
    rng = np.random.default_rng(SEED + 3)
    grid = S.FINE
    sims = lambda t, d: {k: V.daily(F_r20(k), d, t.poly_lid) for k in grid}
    res = {}
    cal, test = M.table("cal"), M.table("test")
    for d in (MON, SAT):
        a, b = cal[cal.day == d].reset_index(drop=True), test[test.day == d].reset_index(drop=True)
        sa, sb = sims(a, d), sims(b, d)
        la = {k: np.log10(np.clip(sa[k], 1, None) / a.obs.values) ** 2 for k in grid}
        lb = {k: float((np.log10(np.clip(sb[k], 1, None) / b.obs.values) ** 2).mean()) for k in grid}
        res[d] = {"test_loss_by_k": lb, "full_choice": min(grid, key=lambda k: la[k].mean()), "subsets": {}}
        for n in (10, 25, 50):
            ch = [min(grid, key=lambda k: la[k][i].mean()) for i in (rng.choice(len(a), min(n, len(a)), replace=False) for _ in range(200))]
            res[d]["subsets"][n] = {"share_choosing": {str(k): ch.count(k) / 200 for k in grid}, "mean_test_loss": float(np.mean([lb[k] for k in ch]))}
    save("e3_k_subsets", res)


def F_r20(k):
    return D.RUNS / "radius_scan" / f"r{int(D.CHERRY_RADIUS_KM)}" / f"k{k:.1f}"


def e3f():
    res = {"runs": []}
    for n, r in F.SUB:
        row = {"n": n, "rep": r, "factors": F.sub_factors(n, r, 2)}
        for day in (MON, SAT):
            for name, t in V.sets(day).items():
                o = t.obs.values
                s, b = V.daily(out_of(f"sub{n}_{r}_r2"), day, t.poly_lid), V.daily(MODEL, day, t.poly_lid)
                row[f"{day}_{name}"] = {"sd": V.metrics(s, o)["sd_log10"], "sd_model": V.metrics(b, o)["sd_log10"], "median": V.metrics(s, o)["median_abs_log10"], "median_model": V.metrics(b, o)["median_abs_log10"], "spearman": V.metrics(s, o)["spearman"], "ratio": V.metrics(s, o)["ratio"]}
        res["runs"].append(row)
    save("e3_factor_subsets", res)


def e3c():
    res = {}
    rows = []
    for sim_tag, label in (("sim_200210", "2020-02-10"), ("sim_210628", "2021-06-28")):
        work = F.OUT / "correction_curve"
        work.mkdir(parents=True, exist_ok=True)
        for f in MODEL.glob(f"{sim_tag}_*"):
            if "uniq" in f.name or "barriers" in f.name or "cartodata" in f.name:
                shutil.copy2(f, work / f.name)
        sim = P.corrector(str(work / sim_tag))
        sim.recursion_max_depth = 3
        raw = pd.read_csv(sim.unique_file, sep=";")
        cols = [c for c in raw if c.startswith("20")]
        mapped = sorted({int(c.split("_")[0]) for c in sim.dfc.columns})
        comp = [c for c in mapped if all(f"{c}_{x}" in sim.dfc for x in ("IN", "OUT")) and sim.dfc[[f"{c}_IN", f"{c}_OUT"]].notna().all().all()]
        base_map = dict(sim.poly2coil)
        for rep in range(5):
            rng = np.random.default_rng(SEED + 40 + rep)
            perm = list(rng.permutation(comp))
            nt = max(2, round(0.2 * len(perm)))
            test = perm[:nt]
            links = {sim.coil2poly[c] for c in test}
            pool = [c for c in perm[nt:] if sim.coil2poly[c] not in links]
            for frac in (0.25, 0.5, 0.75, 1.0):
                use = pool[:int(round(frac * len(pool)))]
                sim.poly2coil = {p: c for p, c in base_map.items() if p not in links and c in use}
                with contextlib.redirect_stdout(io.StringIO()):
                    out = pd.read_csv(sim.correct(use, suffix="curve"), sep=";")
                ar = ac = tot = 0.0
                for c in test:
                    pc = sim.coil2poly[c]
                    for dc, ow in (("IN", "FT"), ("OUT", "TF")):
                        o = sim.dfc[f"{c}_{dc}"].values.astype(float)
                        r = raw[(raw.poly_cid == pc) & (raw.oneway == ow)][cols].values.ravel().astype(float)
                        a = out[(out.poly_cid == pc) & (out.oneway == ow)][cols].values.ravel().astype(float)
                        if len(r) == 24 and len(a) == 24:
                            ar += np.abs(r - o).sum()
                            ac += np.abs(a - o).sum()
                            tot += o.sum()
                rows.append(dict(day=label, rep=rep, frac=frac, n_train=len(use), n_test=len(test), raw=100 * ar / tot, corrected=100 * ac / tot))
                print(rows[-1], flush=True)
    t = pd.DataFrame(rows)
    res["by_fraction"] = t.groupby(["day", "frac"]).agg(n=("n_train", "mean"), raw=("raw", "mean"), corrected=("corrected", "mean"), min_gain=("raw", lambda s: float((s - t.loc[s.index, "corrected"]).min())), max_gain=("raw", lambda s: float((s - t.loc[s.index, "corrected"]).max()))).reset_index().to_dict("records")
    t.to_csv(RES / "e3_correction_curve.csv", index=False)
    save("e3_correction_curve", res)


def link_daily_cid(path, day):
    u = pd.read_csv(next(Path(path).glob(f"sim_{D.tag(day)}_uniq_*.csv")), sep=";")
    return u.groupby("poly_cid")[[c for c in u if c.startswith("20")]].sum().sum(axis=1)


def e4():
    rng, res = np.random.default_rng(SEED + 4), {"gps": {}, "detectors": {}, "alpha": {}}
    keep = set(pd.read_csv(R1 / "private/gps_links_unchanged.csv", index_col=0).query("hausdorff_m <= 1").index)
    v = pd.read_csv(ROOT / "work_viasat/viasat_20200210_20200218_timed_fluxes.csv", sep=";", parse_dates=["time"])
    v = v[v.cid.isin(keep)]
    fc = G.fc_links()
    runs = {"V6": MODEL} | {n[2:]: out_of(n) for n in F.ROUTES}
    for day in (MON, SAT):
        g = v[v.time.dt.date == pd.Timestamp(day).date()].groupby("cid").total_fluxes.sum()
        g = g[(g > 0) & g.index.isin(fc)]
        s = {k: link_daily_cid(p, day).reindex(g.index).fillna(0).values for k, p in runs.items()}
        o = g.values
        idx = [rng.integers(0, len(o), len(o)) for _ in range(N_BOOT)]
        res["gps"][day] = {"links": len(o), "spearman": {k: float(spearmanr(o, x)[0]) for k, x in s.items()},
                           "other_minus_V6_ci95": {k: ci([spearmanr(o[i], s[k][i])[0] - spearmanr(o[i], s["V6"][i])[0] for i in idx]) for k in s if k != "V6"}}
    prov = PD.PROV
    pairs = {"V1_vs_V0": ("V1", "V0"), "D1_vs_V0": ("D1", "V0"), "V6_vs_V1": ("V6", "V1"), "V6_vs_D1": ("V6", "D1"), "V6_vs_V0": ("V6", "V0")}
    inside = {"V6_vs_V0": ("V6", "V0")} if D.NO_CODE else {"T1_vs_V0": ("T1", "V0"), "V6_vs_V0": ("V6", "V0"), "T1_vs_V6": ("T1", "V6")}
    for day in (MON, SAT):
        res["detectors"][day] = {}
        for name, t in V.sets(day).items():
            isfc = prov.reindex(t.coil.values).values == "FO"
            for label, mask, ps in (("outside_FC", ~isfc, pairs), ("inside_FC", isfc, inside)):
                q, o = t[mask].reset_index(drop=True), t.obs.values[mask]
                x = {k: V.daily(runs[k], day, q.poly_lid) for k in {a for p in ps.values() for a in p}}
                idx = [rng.integers(0, len(o), len(o)) for _ in range(N_BOOT)]
                med = lambda s, i: np.median(np.abs(np.log10(np.clip(s[i], 1, None) / o[i])))
                res["detectors"][day][f"{name}_{label}"] = {"n": int(len(o)), "spearman": {k: float(spearmanr(o, s)[0]) for k, s in x.items()}, "median": {k: float(med(s, np.arange(len(o)))) for k, s in x.items()},
                    "pairs": {k: {"spearman_ci95": ci([spearmanr(o[i], x[a][i])[0] - spearmanr(o[i], x[b][i])[0] for i in idx]), "median_ci95": ci([med(x[a], i) - med(x[b], i) for i in idx])} for k, (a, b) in ps.items()}}
    t = M.table("cal")
    base = M.daily(lambda d: MODEL, t)
    for n in F.ALPHA:
        res["alpha"][n] = M.compare(t, M.daily(lambda d: out_of(n), t), base, rng)
    res["alpha_replaces"] = [n for n, c in res["alpha"].items() if c["sd_diff_ci95"][1] < 0]
    res["V6_stands"] = not any(all(res["gps"][d]["other_minus_V6_ci95"][k][0] > 0 for d in (MON, SAT)) for k in res["gps"][MON]["other_minus_V6_ci95"])
    save("e4_routing", res)


def e5():
    rng, res = np.random.default_rng(SEED + 5), {}
    cal = M.table("cal")
    for day in (MON, SAT):
        t = cal[cal.day == day].reset_index(drop=True)
        o = t.obs.values
        sel = D.k_of(day)
        s = {sel: V.daily(MODEL, day, t.poly_lid)} | {x: V.daily(out_of(f"k_{x}"), day, t.poly_lid) for x in F.KS[day]}
        err = {k: np.log10(np.clip(v, 1, None) / o) ** 2 for k, v in s.items()}
        idx = [rng.integers(0, len(o), len(o)) for _ in range(N_BOOT)]
        ks = sorted(s)
        res[day] = {"selected": sel, "min_of_grid": min(ks, key=lambda k: err[k].mean()), "by_k": {str(k): {"loss": float(err[k].mean()), "ratio": float(s[k].sum() / o.sum()), "loss_minus_selected_ci95": ci([err[k][i].mean() - err[sel][i].mean() for i in idx])} for k in ks}}
    res["stands"] = all(res[d]["selected"] == res[d]["min_of_grid"] for d in (MON, SAT))
    save("e5_k_with_factors", res)


def e6():
    rng, res = np.random.default_rng(SEED + 6), {}
    cal = M.table("cal")
    choice = {}
    for day in (MON, SAT):
        t = cal[cal.day == day]
        loss = {m: float((np.log10(np.clip(V.daily(out_of(f"ext_m{m}"), day, t.poly_lid), 1, None) / t.obs.values) ** 2).mean()) for m in F.MULT}
        choice[day] = min(loss, key=loss.get)
        res[f"loss_{day}"] = loss
    res["multiplier"] = choice
    path = lambda d: out_of(f"ext_m{choice[d]}")
    b = M.daily(lambda d: MODEL, cal)
    res["calibration"] = M.compare(cal, M.daily(path, cal), b, rng)
    c = res["calibration"]
    res["beats_model"] = bool(c["sd_diff_ci95"][1] < 0 or (c["spearman_diff_ci95"][0] > 0 and c["new"]["sd_log10"] <= c["frozen"]["sd_log10"]))
    res["direction"] = {}
    for half in ("cal", "test"):
        t = M.table(half)
        t = pd.concat([t[t.day == d] for d in C.CAL_DAYS]).reset_index(drop=True)
        x, y = DD.rows(t, path).cor_diff.values, DD.rows(t, lambda d: MODEL).cor_diff.values
        idx = {u: np.where(t.coil.values == u)[0] for u in t.coil.unique()}
        boot = [np.nanmedian(x[i]) - np.nanmedian(y[i]) for i in (np.concatenate([idx[u] for u in rng.choice(list(idx), len(idx))]) for _ in range(N_BOOT))]
        res["direction"][half] = {"extended": float(np.nanmedian(x)), "model": float(np.nanmedian(y)), "difference_ci95": ci(boot)}
    res["direction_rule_met"] = bool(res["direction"]["test"]["difference_ci95"][0] > 0)
    save("e6_more_relations", res)


def e7():
    res = {}
    for name, t in V.sets(SAT).items():
        o = t.obs.values
        m = {"seed1": V.metrics(V.daily(MODEL, SAT, t.poly_lid), o)} | {f"seed{s}": V.metrics(V.daily(out_of(f"seed{s}"), SAT, t.poly_lid), o) for s in (2, 3, 4)}
        res[name] = {"by_seed": m, "range": {k: float(max(x[k] for x in m.values()) - min(x[k] for x in m.values())) for k in ("ratio", "spearman", "sd_log10", "median_abs_log10")}}
    save("e7_seeds", res)


def e8():
    import geopandas as gpd
    rng, res = np.random.default_rng(SEED + 8), {"block": {}}
    g = gpd.read_file(R1 / "carto_a059fb0.geojson").to_crs(32632)
    p = g.geometry.representative_point()
    shapes = gpd.read_file(ROOT / "vars/extra/er-shapes.geojson").to_crs(32632)
    prov = gpd.sjoin(gpd.GeoDataFrame({"cid": g.poly_cid.astype(int)}, geometry=p, crs=32632), shapes[["PRO_NAME", "geometry"]], how="left", predicate="within").drop_duplicates("cid").set_index("cid").PRO_NAME
    grid = pd.Series((p.x // 20000).astype(int).astype(str).values + "_" + (p.y // 20000).astype(int).astype(str).values, index=g.poly_cid.astype(int).values)
    grid = grid[~grid.index.duplicated()]
    PAIRS = {"raw_minus_flat": ("mae_pp_raw", "mae_pp_flat"), "raw_minus_mean": ("mae_pp_raw", "mae_pp_mts"), "raw_minus_od": ("mae_pp_raw", "mae_pp_od"), "corrected_minus_mean": ("mae_pp", "mae_pp_mts"), "corrected_minus_raw": ("mae_pp", "mae_pp_raw")}
    for year in (2020, 2021):
        m = pd.read_csv(R1 / f"private/corrected_link_metrics_{year}_all.csv").set_index("cid")
        m = m[~m.index.isin(G.fc_links())]
        res["block"][year] = {"links": len(m)}
        for label, b in (("link", pd.Series(m.index, index=m.index)), ("grid_20km", grid.reindex(m.index)), ("province", prov.reindex(m.index))):
            ids = {k: v.index.values for k, v in b.dropna().groupby(b.dropna())}
            keys = list(ids)
            res["block"][year][label] = {"blocks": len(keys)}
            for name, (x, y) in PAIRS.items():
                d = (m[x] - m[y])
                res["block"][year][label][name] = {"median": float(d.median()), "ci95": ci([np.median(np.concatenate([d.loc[ids[k]].values for k in rng.choice(keys, len(keys))])) for _ in range(N_BOOT)])}
    t = M.table("test")
    t = pd.concat([t[t.day == d] for d in C.CAL_DAYS]).reset_index(drop=True)
    r = DD.rows(t, lambda d: MODEL)
    r = r[r.mapped]
    res["direction_mapping"] = {"rows": len(r), "median_cor_map": float(r.cor_map.median()), "median_cor_swap": float(r.cor_swap.median()), "share_swap_better": float((r.cor_swap > r.cor_map).mean()), "share_swap_better_by_0.1": float((r.cor_swap > r.cor_map + 0.1).mean())}
    res["detector_153"] = "link 3589 has oneway = 3 (closed) in vars/carto/er-speed.pro and is removed from the graph; see the data section"
    save("e8_offline", res)


if __name__ == "__main__":
    {"e1": e1, "e2": e2, "e3k": e3k, "e3f": e3f, "e3c": e3c, "e4": e4, "e5": e5, "e6": e6, "e7": e7, "e8": e8}[sys.argv[1]]()
