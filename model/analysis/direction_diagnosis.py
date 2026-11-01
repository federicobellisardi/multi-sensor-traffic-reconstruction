#!/usr/bin/env python3
"""Volumes by direction of travel: calibration half for the description, test half for the rule below. Selects nothing.

Volumes in the calibration and validation of the demand sum both directions, while the correction and the leave-one-out test
use them separately. Here: error by direction split into level and split between directions, whether the pivot mapping of
the directions holds, and detectors whose link has simulated flow in one direction only. Directional signal of a detector:
correlation over the 24 hours between observed and simulated difference of the two directions.

Rule fixed after the calibration half was seen and before the test half was read (31 Oct): the OD relations carry directional
information if on the test half the 95% paired bootstrap interval over detectors of the difference in median directional
signal, N100 (multiplier 1.15, without code 000000000) minus frozen, lies above zero. The same is reported for frozen minus
the simulation without OD structure. Exploratory: it changes no model setting. 2021 has no run with more relations.

  python3 direction_diagnosis.py -> model/results/demand/direction_diagnosis.json
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calibrate_demand as C  # noqa: E402
import demand_scaling as D  # noqa: E402
import od_matrix as M  # noqa: E402
import reconstruct_and_validate as P  # noqa: E402
import source_value as V  # noqa: E402
from paths import ROOT  # noqa: E402

N_BOOT, SEED = 2000, 20261046
RUNS = {"frozen": M.frozen_path, "no_od": lambda d: D.RUNS / "source_value/no_od", "N100": lambda d: M.OUT / "N100_r20_x_m1.15",
        "N200": lambda d: M.OUT / "N200_r20_x_m1.3", "N347_with_code": lambda d: M.OUT / "N347_r20"}
ONE_WAY_SHARE = 0.01  # a simulated direction below this share of the link total counts as no flow


def pivot():
    p = pd.read_csv(ROOT / "vars/extra/correction-pivot-mapping.csv", sep=";")
    out = {}
    for coil, dr, dc in p[["coil_id", "dir_reg", "dir_carto"]].values:
        ft = "FT" if dc == "IN" else "TF"
        out[int(coil), int(dr != 0)] = ft
        out[int(coil), int(dr == 0)] = "TF" if ft == "FT" else "FT"
    return out


def hourly_obs():
    obs = P.coil_table_local(2020)
    res = {}
    for sim_day, (days, _) in D.GROUPS.items():
        z = obs[np.isin(obs.index.strftime("%Y-%m-%d"), days)]
        q = z.groupby(z.index.strftime("%H:%M")).mean()
        res[sim_day] = q.groupby(q.index.str[:2]).sum()
    return res


def rows(t, path_of=M.frozen_path):
    pv, obs = pivot(), hourly_obs()
    out = []
    for day in C.CAL_DAYS:
        u = pd.read_csv(next(path_of(day).glob(f"sim_{D.tag(day)}_uniq_*.csv")), sep=";")
        cols = [c for c in u if c.startswith("20")]
        u = u.groupby(["poly_lid", "oneway"])[cols].sum()
        o = obs[day]
        for coil, lid in t[t.day == day][["coil", "poly_lid"]].values:
            if (coil, 0) not in pv:
                out.append(dict(day=day, coil=coil, mapped=False))
                continue
            a, b = o[f"{coil}_0"].values, o[f"{coil}_1"].values
            s = {w: u.loc[(lid, w)].values.astype(float) if (lid, w) in u.index else np.zeros(24) for w in ("FT", "TF")}
            sa, sb = s[pv[coil, 0]], s[pv[coil, 1]]
            cor = lambda x, y: np.corrcoef(x, y)[0, 1] if x.std() > 0 and y.std() > 0 else np.nan
            out.append(dict(day=day, coil=coil, mapped=True, oa=a.sum(), ob=b.sum(), sa=sa.sum(), sb=sb.sum(),
                            cor_map=np.nanmean([cor(a, sa), cor(b, sb)]), cor_swap=np.nanmean([cor(a, sb), cor(b, sa)]), cor_diff=cor(a - b, sa - sb)))
    return pd.DataFrame(out)


def signal():
    rng = np.random.default_rng(SEED)
    out = {}
    for half in ("cal", "test"):
        t = M.table(half)
        t = pd.concat([t[t.day == d] for d in C.CAL_DAYS]).reset_index(drop=True)
        x = {k: rows(t, f).cor_diff.values for k, f in RUNS.items()}
        idx = {c: np.where(t.coil.values == c)[0] for c in t.coil.unique()}
        boot = lambda a, b: [float(q) for q in np.percentile([(lambda i: np.nanmedian(x[a][i]) - np.nanmedian(x[b][i]))(np.concatenate([idx[c] for c in rng.choice(list(idx), len(idx))])) for _ in range(N_BOOT)], [2.5, 97.5])]
        out[half] = {"rows": int(len(t)), "detectors": len(idx), "median": {k: float(np.nanmedian(v)) for k, v in x.items()}, "share_positive": {k: float((v > 0).mean()) for k, v in x.items()},
                     "N100_minus_frozen_ci95": boot("N100", "frozen"), "frozen_minus_no_od_ci95": boot("frozen", "no_od"), "N100_minus_no_od_ci95": boot("N100", "no_od")}
    return out


def main():
    r = rows(M.table("cal"))
    n_all, un = len(r), int((~r.mapped).sum())
    r = r[r.mapped].copy()
    r["st"], r["ot"] = r.sa + r.sb, r.oa + r.ob
    r = r[(r.ot > 0) & (r.st > 0) & (r.oa > 0) & (r.ob > 0)]
    r["one_way"] = np.minimum(r.sa, r.sb) < ONE_WAY_SHARE * r.st
    two = r[~r.one_way]
    log = lambda s, o: np.log10(np.clip(s, 1, None) / o)
    level = log(r.st, r.ot)
    d = np.concatenate([log(two.sa, two.oa), log(two.sb, two.ob)])
    o_d = np.concatenate([two.oa, two.ob])
    s_d = np.concatenate([two.sa, two.sb])
    split_err = (two.sa / two.st) - (two.oa / two.ot)
    res = {
        "rows": n_all, "without_mapping": un, "usable": int(len(r)),
        "both_directions_sum": {"sd_log10": float(level.std()), "spearman": float(spearmanr(r.ot, r.st)[0])},
        "both_directions_sum_two_way_sites": {"sd_log10": float(log(two.st, two.ot).std()), "spearman": float(spearmanr(two.ot, two.st)[0])},
        "by_direction_two_way_sites": {"values": int(len(d)), "sd_log10": float(d.std()), "spearman": float(spearmanr(o_d, s_d)[0])},
        "split": {"observed_share_sd": float((two.oa / two.ot).std()), "simulated_share_sd": float((two.sa / two.st).std()),
                  "share_spearman": float(spearmanr(two.oa / two.ot, two.sa / two.st)[0]), "median_abs_error": float(split_err.abs().median()),
                  "swapped_median_abs_error": float(((two.sb / two.st) - (two.oa / two.ot)).abs().median()),
                  "share_abs_error_above_0.2": float((split_err.abs() > 0.2).mean())},
        "mapping": {"median_profile_correlation": float(two.cor_map.median()), "median_swapped": float(two.cor_swap.median()),
                    "median_hourly_difference_correlation": float(two.cor_diff.median()), "share_hourly_difference_negative": float((two.cor_diff < 0).mean()),
                    "share_swapped_better": float((two.cor_swap > two.cor_map).mean()),
                    "share_swapped_better_by_0.1": float((two.cor_swap > two.cor_map + 0.1).mean())},
        "simulated_one_way": {"rows": int(r.one_way.sum()), "coils": int(r[r.one_way].coil.nunique()), "median_log10": float(level[r.one_way].median()) if r.one_way.any() else None,
                              "median_log10_others": float(level[~r.one_way].median()), "share_below_half": float((level[r.one_way] < -0.301).mean()) if r.one_way.any() else None,
                              "share_below_half_others": float((level[~r.one_way] < -0.301).mean())},
        "sd_without_simulated_one_way": float(level[~r.one_way].std()),
    }
    res["signal"] = signal()
    p = r.pivot(index="coil", columns="day", values="cor_diff").dropna()
    res["signal_monday_saturday_correlation_frozen"] = {"coils": int(len(p)), "r": float(np.corrcoef(p.iloc[:, 0], p.iloc[:, 1])[0, 1])}
    (D.RES / "direction_diagnosis.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
