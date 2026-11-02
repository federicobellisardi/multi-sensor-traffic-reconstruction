#!/usr/bin/env python3
"""Separates the OD relations from the province factors using runs that already exist; no new simulation.

The published comparison (source_value.py) removes the relations and, with them, the province factors. Here:
  relations_without_factors : frozen model without factors - no relations without factors (the factors enter neither arm)
  factors_with_relations    : model with factors - frozen model without factors (the relations are in both arms)
  relations_and_factors     : model with factors - no relations with the same total (the published, confounded comparison)
There is no run with factors and no relations in which the factors keep their spatial pattern, because they act on sources
with a location, so the interaction of the two cannot be estimated.
Same detector sets, metrics and paired bootstrap as source_value.py. Monday and Saturday.

  python3 od_factor_decomposition.py -> model/results/demand/od_factor_decomposition.json
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
import demand_scaling as D  # noqa: E402
import final_experiments as F  # noqa: E402
import od_matrix as M  # noqa: E402
import source_value as V  # noqa: E402
from paths import ARTICLE  # noqa: E402

N_BOOT, SEED = 2000, 20261049
RUNS = {"model": lambda d: D.OUT / "V6_scaled", "no_factors": M.frozen_path,
        "no_relations": lambda d: V.OUT / "no_od", "no_relations_no_factors": lambda d: F.no_relations_no_factors()}
PAIRS = {"relations_without_factors": ("no_factors", "no_relations_no_factors"),
         "factors_with_relations": ("model", "no_factors"),
         "relations_and_factors": ("model", "no_relations")}


def compare(a, b, o, rng):
    n = len(o)
    keep = np.where((a > 0) & (b > 0))[0]
    sd = lambda s, i: np.log10(s[i] / o[i]).std()
    med = lambda s, i: np.median(np.abs(np.log10(np.clip(s[i], 1, None) / o[i])))
    all_ = np.arange(n)
    idx = [rng.integers(0, n, n) for _ in range(N_BOOT)]
    ds = [spearmanr(o[i], a[i])[0] - spearmanr(o[i], b[i])[0] for i in idx]
    dm = [med(a, i) - med(b, i) for i in idx]
    dv = [sd(a, i) - sd(b, i) for i in (rng.choice(keep, len(keep)) for _ in range(N_BOOT))]
    ci = lambda v: [float(x) for x in np.percentile(v, [2.5, 97.5])]
    return {"n": n, "spearman_a": float(spearmanr(o, a)[0]), "spearman_b": float(spearmanr(o, b)[0]), "spearman_diff": float(spearmanr(o, a)[0] - spearmanr(o, b)[0]), "spearman_diff_ci95": ci(ds),
            "sd_a": float(sd(a, keep)), "sd_b": float(sd(b, keep)), "sd_diff": float(sd(a, keep) - sd(b, keep)), "sd_diff_ci95": ci(dv),
            "median_abs_a": float(med(a, all_)), "median_abs_b": float(med(b, all_)), "median_abs_diff_ci95": ci(dm)}


def table(out):
    names = {"relations_without_factors": "Relations, no factors", "factors_with_relations": "Factors, with relations", "relations_and_factors": "Relations and factors"}
    rows = []
    for p, lab in names.items():
        for s, sl in (("held_out_2020", "Test half, 2020"), ("all_2021", "2021")):
            for day, dl in ((V.MON, "Monday"), (V.SAT, "Saturday")):
                x = out[day][s][p]
                a, b = x["spearman_diff_ci95"], x["sd_diff_ci95"]
                rows.append(f"{lab} & {sl} & {dl} & {x['n']} & {x['spearman_diff']:+.3f} [{a[0]:+.3f}, {a[1]:+.3f}] & {x['sd_diff']:+.3f} [{b[0]:+.3f}, {b[1]:+.3f}] \\\\")
    (ARTICLE / "tables/od_decomposition.tex").write_text("\\begin{table}[htbp]\\centering\n\\caption{Separating the OD relations from the province factors with existing simulations. Differences in Spearman correlation and dispersion of daily volumes, with 95\\% paired bootstrap intervals over detectors (2,000 resamples, seed 20261049). The last block repeats the comparison that also removes the regional pattern of the factors, with a new bootstrap, so its intervals can differ slightly from those of Section S5. Exploratory: added after the results. Dispersion excludes detectors with no simulated traffic.}\n\\label{tab:od_decomposition}\n\\small\n\\begin{tabular}{@{}lllrll@{}}\\toprule\nComparison & Detectors & Day & $n$ & Spearman & Dispersion \\\\\\midrule\n" + "\n".join(rows) + "\n\\bottomrule\\end{tabular}\n\\end{table}\n")


def main():
    rng = np.random.default_rng(SEED)
    out = {"note": __doc__.split("Same detector")[0].strip()}
    for day in (V.MON, V.SAT):
        out[day] = {}
        for name, t in V.sets(day).items():
            o = t.obs.values
            sim = {r: V.daily(f(day), day, t.poly_lid) for r, f in RUNS.items()}
            out[day][name] = {p: compare(sim[a], sim[b], o, rng) for p, (a, b) in PAIRS.items()}
    (D.RES / "od_factor_decomposition.json").write_text(json.dumps(out, indent=1) + "\n")
    table(out)
    for day in (V.MON, V.SAT):
        for s, v in out[day].items():
            for p, x in v.items():
                print(day, s, p, x["n"], "rho", round(x["spearman_a"], 3), round(x["spearman_b"], 3), np.round(x["spearman_diff_ci95"], 3), "sd", round(x["sd_a"], 3), round(x["sd_b"], 3), np.round(x["sd_diff_ci95"], 3), "med", round(x["median_abs_a"], 3), round(x["median_abs_b"], 3), np.round(x["median_abs_diff_ci95"], 3))


if __name__ == "__main__":
    main()
