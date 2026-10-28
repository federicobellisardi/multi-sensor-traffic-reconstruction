#!/usr/bin/env python3
"""LaTeX tables of the Supplementary Material, generated from article1/results."""
import json
from pathlib import Path

import pandas as pd

A1 = Path(__file__).resolve().parents[1]
RES, TAB = A1 / "results", A1 / "tables"
NAMES = {"V0_default_distance": "Shortest distance, default speeds",
         "V1_gps_distance": "Shortest distance, GPS speeds",
         "V2_gps_time": "Travel time, GPS speeds",
         "V3_gps_mixed": "Mixed distance/time, GPS speeds",
         "V4_gps_time_classweights": "Travel time + class transition weights",
         "V5_gps_time_classweights_sqrt": "Travel time + damped class weights",
         "V6_gps_usage_classweights": "Usage cost + class transition weights (selected)"}


def table(name, caption, label, header, rows, align):
    t = [r"\begin{table}[htbp]\centering", rf"\caption{{{caption}}}", rf"\label{{{label}}}",
         rf"\begin{{tabular}}{{@{{}}{align}@{{}}}}\toprule", header + r" \\\midrule"]
    t += [" & ".join(map(str, r)) + r" \\" for r in rows]
    t += [r"\bottomrule\end{tabular}\end{table}"]
    (TAB / name).write_text("\n".join(t) + "\n")


def main():
    r = pd.read_csv(RES / "routing/routing_variants_2020-02-10.csv")
    table("routing_variants.tex",
          "Route-choice variants simulated for 10 February 2020. Calibration: Spearman correlation between "
          "simulated daily link volumes and GPS counts on Forl\\`i--Cesena links. Detectors: Spearman correlation "
          "with the daily volumes of the coils outside Forl\\`i--Cesena complete on that day (not used for selection). "
          "Main roads: share of simulated vehicle-kilometres on motorway, trunk and primary links.",
          "tab:routing", "Variant & GPS links & Calibration $\\rho_s$ & Detectors & Detector $\\rho_s$ & Main roads",
          [(NAMES[v.variant], v.calib_gps_links, f"{v.calib_spearman_gps:.3f}", v.valid_coils_outside_FC,
            f"{v.valid_spearman_coils:.3f}", f"{v.share_volume_main_roads:.2f}") for v in r.itertuples()], "lrrrrr")
    loo = json.load(open(RES / "corrected/loo_summary.json"))
    rows = []
    for y, d in loo.items():
        rows.append((y, d["coils"], d["coil_days"], f"{d['pooled_raw_error_pct']:.1f}", f"{d['pooled_loo_error_pct']:.1f}",
                     f"{d['median_coil_raw_pct']:.1f}", f"{d['median_coil_loo_pct']:.1f}",
                     f"{100*d['share_reached']:.0f}", f"{100*d['share_improved']:.0f}", f"{100*d['share_worse']:.0f}",
                     f"{d['volume_spearman']:.2f}", f"{d['loo_volume_spearman']:.2f}"))
    table("loo.tex",
          "Leave-one-detector-out test. Errors are $\\sum|\\tilde u-c|/\\sum c$ in percent of the observed volume, "
          "pooled over coils or as the median over coils; reached: share of withheld coils whose link is modified by "
          "the propagation from other coils; improved/worse: share with lower/higher error than the simulation before correction; "
          "$\\rho_s$: Spearman correlation of daily volumes with the observed ones before correction and with the detector withheld.",
          "tab:loo", "Year & Coils & Coil-days & Pooled raw & Pooled LOO & Median raw & Median LOO & Reached (\\%) & Improved (\\%) & Worse (\\%) & $\\rho_s$ raw & $\\rho_s$ LOO",
          rows, "lrrrrrrrrrrr")
    s = pd.read_csv(RES / "corrected/sensitivity_coverage_depth_summary.csv")
    s = s[s.frac == 1.0]
    table("depth.tex",
          "Change of the pooled error (percentage points of observed volume) on a fixed random 20\\% of the complete "
          "coils of each 2020 day when all other coils are assimilated with the given propagation depth. "
          f"Raw error of the test coils: {s.raw_error_pct.iloc[0]:.1f}\\%. Negative values are increases of the error.",
          "tab:depth", "Depth (polylines) & Error reduction (pp)",
          [(int(v.depth), f"{v['mean']:.1f}") for _, v in s.iterrows()], "rr")
    e = pd.read_csv(RES / "corrected/error_vs_detector_distance.csv")
    table("distance.tex",
          "Median hourly-share MAE (pp) of the raw and assimilated reconstruction on GPS links by network distance "
          "from the nearest coil (polylines).",
          "tab:distance", "Year & Distance & Links & Raw & Assimilated & Reduction",
          [(int(v.year), v.hop_class, int(v.links), f"{v.mae_raw:.2f}", f"{v.mae_assim:.2f}", f"{v.gain_pp:.2f}")
           for v in e.itertuples()], "lrrrrr")
    val = json.load(open(RES / "corrected/validation_summary.json"))
    rows = []
    for y in ("2020", "2021"):
        for k, d in val[y]["probe_strata"].items():
            rows.append((y, k, d["links"], f"{d['mae_pp']:.2f}", f"{d['mae_pp_mts']:.2f}", f"{d['pearson']:.2f}"))
    table("probe_strata.tex",
          "Hourly-share MAE (pp) by number of GPS probes per link and campaign: reconstruction, mean MTS profile and "
          "hourly correlation of the reconstruction (medians).",
          "tab:probes", "Campaign & Probes & Links & Reconstruction & MTS & Correlation", rows, "llrrrr")
    base = json.load(open(RES / "baseline_v0/validation_summary.json"))
    rows = []
    for y in ("2020", "2021"):
        for lab, src in [("shortest distance", base), ("GPS-informed", val)]:
            d = src[y]["day_types"]["all"]
            rows.append((y, lab, d["links"], f"{d['mae_pp_raw']['median']:.2f}"))
    table("routing_shape.tex",
          "Median hourly-share MAE (pp) of the simulation before detector correction on all usable GPS links, with "
          "shortest-distance and GPS-informed route choice.", "tab:routing_shape",
          "Campaign & Route choice & Links & MAE (pp)", rows, "llrr")
    cmp = json.load(open(RES / "corrected/routing_comparison.json"))
    rows = []
    for y, d in cmp.items():
        lo, hi = d["diff_ci95"]
        rows.append((y, d["detectors"], f"{d['spearman_base']:.2f}", f"{d['spearman_gps']:.2f}",
                     f"{d['diff']:.2f} [{lo:.2f}, {hi:.2f}]", f"{d['median_abs_log10_ratio_base']:.2f}",
                     f"{d['median_abs_log10_ratio_gps']:.2f}"))
    table("routing_volumes.tex",
          "Daily volumes of the simulation before detector correction at the coils outside Forl\\`i--Cesena: Spearman "
          "correlation with the observed volumes for shortest-distance and GPS-informed route choice, paired bootstrap "
          "difference with 95\\% interval (5,000 resamples of coils), and median absolute $\\log_{10}$ ratio of "
          "simulated to observed volume.", "tab:routing_volumes",
          "Campaign & Coils & $\\rho_s$ distance & $\\rho_s$ GPS & Difference & $|\\log_{10}|$ distance & $|\\log_{10}|$ GPS",
          rows, "lrrrlrr")
    sc = pd.read_csv(RES / "demand/scan_summary.csv")
    sc = sc[sc.part != "all"]
    rows = []
    for (run, part), d in sc.groupby(["run", "part"], sort=False):
        d = d.iloc[0]
        rows.append((run if run.startswith("per") else f"$k={float(run):.1f}$", part, int(d.n), f"{d.ratio:.2f}",
                     f"{d.spearman:.2f}", f"{d.median_abs_log10:.2f}", f"{100 * d.within_factor2:.0f}"))
    table("demand_scan.tex",
          "Daily volumes on the complete coils of 10 February 2020 for the historic pair-level rescaling and for common "
          "demand factors $k$: pooled simulated/observed ratio, Spearman correlation, median absolute $\\log_{10}$ ratio "
          "and share of coils within a factor of two, on the calibration and test halves.", "tab:scan",
          "Demand & Coils & $n$ & Ratio & $\\rho_s$ & $|\\log_{10}|$ & Within $\\times2$ (\\%)", rows, "llrrrrr")
    print("tables written")


if __name__ == "__main__":
    main()
