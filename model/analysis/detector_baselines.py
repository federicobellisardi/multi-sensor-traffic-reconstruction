#!/usr/bin/env python3
"""Simple detector-only predictors against the frozen simulation, and sensitivity to the completeness filter.

No simulation enters a baseline. Level: median volume of the other detectors of the same road class. Profile: mean
normalized profile of the other detectors.
1. Held-out half, February 2020, by day type: baselines built on the calibration half only, compared with the raw
   simulation at 15 min and on daily volumes.
2. Leave-one-out records (corrected/loo_detectors.csv): same records and same hourly error; baselines built on the
   other coils of the same day. A fair competitor of the correction, which also uses the other coils of that day.
3. Completeness filter: raw simulation on complete coil-days against coil-days in which missing quarters are isolated
   (at most 20, longest gap 4) and are read as zero counts.
Bootstrap over detectors. Nothing is to be selected on this.

  python3 detector_baselines.py -> model/results/corrected/detector_baselines.json
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
import delay_quarter as Q  # noqa: E402
import demand_scaling as D  # noqa: E402
import frozen_validation as F  # noqa: E402
import reconstruct_and_validate as P  # noqa: E402
from paths import ROOT  # noqa: E402

N_BOOT, SEED = 2000, 20261041
OUT = ROOT / "model/results/corrected"
RUNS = D.RUNS / "demand/V6_scaled"
BAR = pd.read_csv(ROOT / "vars/extra/er_barriers_cartodata.csv", sep=";").drop_duplicates("tag").set_index("tag").poly_lid


def lid_class():
    u = pd.read_csv(next(RUNS.glob("sim_200210_uniq_*.csv")), sep=";", usecols=["poly_lid", "poly_cid"]).drop_duplicates("poly_lid")
    rc = pd.read_csv(ROOT / "model/results/road_class.csv").set_index("poly_cid").road_class
    return u.set_index("poly_lid").poly_cid.map(rc)


CLS = lid_class()


def volume_metrics(s, o):
    lr = np.log10(np.clip(s, 1, None) / o)
    return {"n": int(len(o)), "ratio": float(s.sum() / o.sum()), "spearman": float(spearmanr(o, s)[0]), "median_abs_log10": float(np.median(np.abs(lr))),
            "within_factor2": float(np.mean(np.abs(lr) < np.log10(2)))}


def boot(rng, n, f):
    v = [f(rng.integers(0, n, n)) for _ in range(N_BOOT)]
    return [float(x) for x in np.percentile(v, [2.5, 97.5])]


def held_out(day, rng):
    Q.DAY = day
    coil, obs, sim = Q.load(F.OUT, check=False, test=True)
    cc, co, _ = Q.load(F.OUT, check=False, test=False)
    prof = (co / co.sum(axis=1, keepdims=True)).mean(axis=0)
    vol = pd.Series(co.sum(axis=1), index=cc).groupby(CLS.reindex(BAR.reindex(cc).values).values).median()
    all_median = float(np.median(co.sum(axis=1)))
    level = np.array([vol.get(CLS.get(BAR[c]), all_median) for c in coil])
    base = np.outer(level, prof)
    daily_o, daily_s = obs.sum(axis=1), sim.sum(axis=1)
    h = lambda x, i=slice(None): np.abs(Q.hourly(x[i]) - Q.hourly(obs[i])).sum()
    corr = lambda x: np.array([np.corrcoef(a, b)[0, 1] if b.std() > 0 else np.nan for a, b in zip(obs, x)])
    corr_s, corr_b = corr(sim), corr(np.outer(daily_o, prof))
    oracle = lambda x: 100 * np.abs(Q.hourly(x) - Q.hourly(obs)).sum() / obs.sum()
    rescale = lambda x: x * (daily_o / np.where(x.sum(axis=1) > 0, x.sum(axis=1), 1))[:, None]
    n = len(coil)
    return {"detectors": n, "calibration_detectors": int(len(cc)),
            "daily": {"simulation": volume_metrics(daily_s, daily_o), "class_median": volume_metrics(level, daily_o),
                      "median_abs_log10_sim_minus_base_ci95": boot(rng, n, lambda i: np.median(np.abs(np.log10(np.clip(daily_s[i], 1, None) / daily_o[i]))) - np.median(np.abs(np.log10(level[i] / daily_o[i])))),
                      "spearman_sim_minus_base_ci95": boot(rng, n, lambda i: spearmanr(daily_o[i], daily_s[i])[0] - spearmanr(daily_o[i], level[i])[0])},
            "hourly_error_pct": {"simulation": float(100 * h(sim) / obs.sum()), "class_median_mean_profile": float(100 * h(base) / obs.sum()),
                                 "sim_minus_base_ci95_pp": boot(rng, n, lambda i: 100 * (h(sim, i) - h(base, i)) / obs[i].sum())},
            "known_level_error_pct": {"simulation": oracle(rescale(sim)), "mean_profile": oracle(rescale(base))},
            "profile_correlation_median": {"simulation": float(np.nanmedian(corr_s)), "mean_profile": float(np.nanmedian(corr_b))},
            "profile_correlation_diff_median_ci95": boot(rng, n, lambda i: np.nanmedian(corr_s[i]) - np.nanmedian(corr_b[i]))}


def loo_baseline(rng):
    d = pd.read_csv(OUT / "loo_detectors.csv").dropna(subset=["raw_abs", "loo_abs"]).reset_index(drop=True)
    d["year"] = d.day.str[:4].astype(int)
    d["road_class"] = CLS.reindex(BAR.reindex(d.coil).values).values
    res = {}
    for y, g in d.groupby("year"):
        z = P.coil_table_local(y)
        H = {}
        for day, gd in g.groupby("day"):
            q = z[z.index.strftime("%Y-%m-%d") == day]
            hourly = q.groupby(q.index.hour).sum(min_count=4)
            for i, c, tot in gd[["coil", "obs_total"]].itertuples():
                cand = [hourly[f"{c}_{k}"].values for k in (0, 1)]
                H[i] = min(cand, key=lambda v: abs(np.nansum(v) - tot))
        g = g.assign(base_abs=np.nan)
        for day, gd in g.groupby("day"):
            for i, r in gd.iterrows():
                o = gd[gd.coil != r.coil]
                prof = np.mean([H[j] / H[j].sum() for j in o.index], axis=0)
                same = o[o.road_class == r.road_class]
                level = (same if len(same) >= 3 else o).obs_total.median()
                g.loc[i, "base_abs"] = np.abs(level * prof - H[i]).sum()
        by = g.groupby("coil")[["obs_total", "raw_abs", "loo_abs", "base_abs"]].sum()
        pct = lambda k, b=by: float(100 * b[k].sum() / b.obs_total.sum())
        res[str(y)] = {"coils": int(len(by)), "raw_pct": pct("raw_abs"), "loo_pct": pct("loo_abs"), "baseline_pct": pct("base_abs"),
                       "loo_minus_baseline_ci95_pp": boot(rng, len(by), lambda i: pct("loo_abs", by.iloc[i]) - pct("base_abs", by.iloc[i])),
                       "raw_minus_baseline_ci95_pp": boot(rng, len(by), lambda i: pct("raw_abs", by.iloc[i]) - pct("base_abs", by.iloc[i])),
                       "share_coils_loo_better_than_baseline": float((by.loo_abs < by.base_abs).mean())}
    return res


def completeness():
    days = sorted(pd.read_csv(OUT / "loo_detectors.csv").day.unique())
    rows = []
    tab = {}
    for day in days:
        y = int(day[:4])
        z = tab.setdefault(y, P.coil_table_local(y))
        q = z[z.index.strftime("%Y-%m-%d") == day]
        u = pd.read_csv(next(RUNS.glob(f"sim_{D.tag(day)}_uniq_*.csv")), sep=";")
        cols = [c for c in u if c.startswith("20")]
        sim = u.groupby("poly_lid")[cols].sum()
        for c, l in BAR.items():
            cc = [f"{c}_0", f"{c}_1"]
            if not all(x in q for x in cc) or l not in sim.index:
                continue
            m = q[cc].isna()
            n = int(m.sum().sum())
            gap = max(int(m[x].astype(int).groupby((~m[x]).cumsum()).sum().max()) for x in cc)
            if n > 20 or gap > 4:
                continue
            o = q[cc].fillna(0).sum(axis=1)
            oh = o.groupby(q.index.hour).sum().values
            s = sim.loc[l].values.astype(float)
            rows.append(dict(year=y, day=day, coil=c, complete=n == 0, obs=oh.sum(), sim=s.sum(), abs=np.abs(s - oh).sum(), night_missing=int(m[q.index.hour < 6].sum().sum()), missing=n))
    r = pd.DataFrame(rows)
    def summ(x):
        return {"coil_days": int(len(x)), "coils": int(x.coil.nunique()), "median_daily_obs": float(x.obs.median()), "ratio": float(x.sim.sum() / x.obs.sum()), "pooled_hourly_error_pct": float(100 * x["abs"].sum() / x.obs.sum()),
                "median_coil_day_error_pct": float((100 * x["abs"] / x.obs).median()), "median_abs_log10": float(np.median(np.abs(np.log10(x.sim.clip(lower=1) / x.obs))))}
    return {str(y): {"complete": summ(g[g.complete]), "isolated_missing_read_as_zero": summ(g[~g.complete]), "union": summ(g),
                     "share_missing_before_06h": float(g.night_missing.sum() / max(g.missing.sum(), 1))} for y, g in r.groupby("year")}


def main():
    rng = np.random.default_rng(SEED)
    out = {"held_out": {F.NAMES[d]: held_out(d, rng) for d in F.C.CAL_DAYS}, "leave_one_out": loo_baseline(rng), "completeness": completeness()}
    (OUT / "detector_baselines.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
