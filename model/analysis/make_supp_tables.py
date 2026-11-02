#!/usr/bin/env python3
"""LaTeX tables of the Supplementary Material, generated from model/results."""
import json
from pathlib import Path

import pandas as pd
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import ARTICLE as A1, RESULTS as R1  # noqa: E402

RES, TAB = R1, A1 / "tables"
NAMES = {"V0_default_distance": "Shortest distance, default speeds",
         "V1_gps_distance": "Shortest distance, GPS speeds",
         "V2_gps_time": "Travel time, GPS speeds",
         "V3_gps_mixed": "Mixed distance/time, GPS speeds",
         "V4_gps_time_classweights": "Travel time + class transition weights",
         "V5_gps_time_classweights_sqrt": "Travel time + damped class weights",
         "V6_gps_usage_classweights": "Usage cost + class transition weights (selected)"}


def table(name, caption, label, header, rows, align):
    t = [r"\begin{table}[htbp]\centering", rf"\caption{{{caption}}}", rf"\label{{{label}}}",
         rf"\resizebox{{\textwidth}}{{!}}{{\begin{{tabular}}{{@{{}}{align}@{{}}}}\toprule", header + r" \\\midrule"]
    t += [" & ".join(map(str, r)) + r" \\" for r in rows]
    t += [r"\bottomrule\end{tabular}}\end{table}"]
    (TAB / name).write_text("\n".join(t) + "\n")


def main():
    r = pd.read_csv(RES / "routing/routing_variants_2020-02-10.csv")
    table("routing_variants.tex",
          "Route-choice variants simulated for 10 February 2020. Calibration: Spearman correlation between "
          "simulated daily link volumes and GPS counts on Forl\\`i--Cesena links. Detectors: Spearman correlation "
          "with the daily volumes of the detectors outside Forl\\`i--Cesena complete on that day (not used for selection). "
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
          "pooled over detectors or as the median over detectors; reached: share of left-out detectors whose link is modified by "
          "the spreading from other detectors; improved/worse: share with lower/higher error than the simulation before correction; "
          "$\\rho_s$: Spearman correlation of daily volumes with the observed ones before correction and with the detector left-out.",
          "tab:loo", "Year & Detectors & Detector-days & Pooled raw & Pooled LOO & Median raw & Median LOO & Reached (\\%) & Improved (\\%) & Worse (\\%) & $\\rho_s$ raw & $\\rho_s$ LOO",
          rows, "lrrrrrrrrrrr")
    s = json.load(open(RES / "corrected/depth_selection.json"))
    table("depth.tex",
          "Reduction of the pooled error (percentage points of observed volume) on left-out detectors, 5-fold cross-validation over "
          f"the {s['detectors']} detectors of 2020 complete on each day, with bootstrap 95\\% intervals over detectors; difference: paired with "
          f"the selected depth {s['selected_depth']}, the smallest within one standard error ({s['se_of_best']:.1f} pp) of the best depth. "
          f"Raw error: {s['raw_error_pct']:.1f}\\%.",
          "tab:depth", "Depth (links) & Error reduction (pp) & 95\\% interval & Difference (pp) & 95\\% interval",
          [(k, f"{v:.1f}", "[{:.1f}, {:.1f}]".format(*s["ci95"][k]),
            *((f"{s['paired_vs_selected'][k]['diff_pp']:+.1f}", "[{:+.1f}, {:+.1f}]".format(*s["paired_vs_selected"][k]["ci95"]))
              if k in s["paired_vs_selected"] else ("--", "--"))) for k, v in s["reduction_pp"].items()], "rrlrl")
    cmp = json.load(open(RES / "corrected/routing_comparison.json"))
    rows = []
    for y, d in cmp.items():
        lo, hi = d["diff_ci95"]
        rows.append((y, d["detectors"], f"{d['spearman_base']:.2f}", f"{d['spearman_gps']:.2f}",
                     f"{d['diff']:.2f} [{lo:.2f}, {hi:.2f}]", f"{d['median_abs_log10_ratio_base']:.2f}",
                     f"{d['median_abs_log10_ratio_gps']:.2f}"))
    table("routing_volumes.tex",
          "Daily volumes of the simulation before detector correction at the detectors outside Forl\\`i--Cesena: Spearman "
          "correlation with the observed volumes for shortest-distance and GPS-informed route choice, paired bootstrap "
          "difference with 95\\% interval (5,000 resamples of detectors), and median absolute $\\log_{10}$ ratio of "
          "simulated to observed volume.", "tab:routing_volumes",
          "Campaign & Detectors & $\\rho_s$ distance & $\\rho_s$ GPS & Difference & $|\\log_{10}|$ distance & $|\\log_{10}|$ GPS",
          rows, "lrrrlrr")
    print("tables written")


if __name__ == "__main__":
    main()
