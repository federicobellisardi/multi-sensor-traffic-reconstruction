#!/usr/bin/env python3
"""GPS validation restricted to the links of Forli-Cesena: test T4, paired differences and the supplementary tables.

  python3 gps_fc.py -> model/results/experiments/gps_fc.json, model/manuscript/tables/{probe_strata,routing_shape}.tex
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gps_validation_split as G  # noqa: E402
import validation_tests as T  # noqa: E402
from paths import ARTICLE, RESULTS as R1  # noqa: E402

BINS = {"1-49": (1, 50), "50-199": (50, 200), "200+": (200, np.inf)}


def main():
    fc = G.fc_links()
    res, rows, shape = {}, [], []
    tests = json.load(open(R1 / "corrected/validation_tests.json"))
    p = {f"{s}_{t}": tests[s][f"{t}_p"] for s in ("2020_test", "2021") for t in ("T2", "T3")}
    for y, name in ((2020, "2020_test"), (2021, "2021")):
        m = pd.read_csv(R1 / f"private/corrected_link_metrics_{y}_all.csv")
        m = m[m.cid.isin(fc)]
        d = (m.mae_pp_raw - m.mae_pp_flat).dropna()
        res[y] = {"links": len(m), **{c: float(m[c].median()) for c in ("mae_pp", "mae_pp_raw", "mae_pp_mts", "mae_pp_od", "mae_pp_flat")}, "share_better_than_flat": float((d < 0).mean()), "T4_p": float(wilcoxon(d, alternative="less").pvalue)}
        p[f"{name}_T4"] = res[y]["T4_p"]
        for k, (a, b) in BINS.items():
            z = m[(m.gps_total >= a) & (m.gps_total < b)]
            rows.append(f"{y} & {k} & {len(z)} & {z.mae_pp.median():.2f} & {z.mae_pp_mts.median():.2f} & {z.pearson.median():.2f} \\\\")
        b = pd.read_csv(R1 / f"private/baseline_v0/corrected_link_metrics_{y}_all.csv")
        b = b[b.cid.isin(fc)]
        res[y]["shortest_distance_raw"] = float(b.mae_pp_raw.median())
        shape += [f"{y} & shortest distance & {len(b)} & {b.mae_pp_raw.median():.2f} \\\\", f"{y} & GPS-informed & {len(m)} & {m.mae_pp_raw.median():.2f} \\\\"]
    res["holm"] = T.holm(p)
    split = json.load(open(R1 / "corrected/gps_validation_split.json"))
    res["paired"] = {y: split[y]["all"]["forli_cesena"]["paired"] for y in ("2020", "2021")}
    for day in ("weekday", "weekend"):
        res[f"paired_{day}"] = {y: split[y][day]["forli_cesena"] for y in ("2020", "2021")}
    (R1 / "experiments/gps_fc.json").write_text(json.dumps(res, indent=1, default=float) + "\n")
    t = ARTICLE / "tables"
    (t / "probe_strata.tex").write_text("\\begin{table}[htbp]\\centering\n\\caption{Hourly-share MAE (pp) on GPS links of Forl\\`i--Cesena, by number of GPS probes per link and campaign: reconstruction, mean detector profile and hourly correlation of the reconstruction (medians).}\n\\label{tab:probes}\n\\begin{tabular}{@{}llrrrr@{}}\\toprule\nCampaign & Probes & Links & Reconstruction & Mean detector & Correlation \\\\\\midrule\n" + "\n".join(rows) + "\n\\bottomrule\\end{tabular}\\end{table}\n")
    (t / "routing_shape.tex").write_text("\\begin{table}[htbp]\\centering\n\\caption{Median hourly-share MAE (pp) of the simulation before detector correction on GPS links of Forl\\`i--Cesena, with shortest-distance and GPS-informed route choice.}\n\\label{tab:routing_shape}\n\\begin{tabular}{@{}llrr@{}}\\toprule\nCampaign & Route choice & Links & MAE (pp) \\\\\\midrule\n" + "\n".join(shape) + "\n\\bottomrule\\end{tabular}\\end{table}\n")
    print(json.dumps(res, default=float)[:3500])


if __name__ == "__main__":
    main()
