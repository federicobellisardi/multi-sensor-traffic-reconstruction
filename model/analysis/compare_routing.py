#!/usr/bin/env python3
"""Paired comparison of raw daily volumes vs MTS detectors outside Forli-Cesena: baseline routing
(results from SIM_BASE) vs GPS-informed routing (SIM_GPS). Spearman difference with a paired
bootstrap over detectors (5,000 resamples, seed 20261028).
Output: model/results/corrected/routing_comparison.json
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import volume_check as V  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import RESULTS as R1, SIM_RUNS  # noqa: E402

RUNS = SIM_RUNS  # simulation outputs (outside the repository)
BASE = str(RUNS / "demand/V0_scaled")
GPS = str(RUNS / "demand/V6_scaled")
OUT = R1 / "corrected/routing_comparison.json"


def main():
    rng = np.random.default_rng(20261028)
    res = {}
    for year in (2020, 2021):
        _, a = V.run(BASE, year, "raw")
        _, b = V.run(GPS, year, "raw")
        m = a.merge(b[["coil", "sim"]], on="coil", suffixes=("_base", "_gps"))
        m = m[m.prov != "FO"].reset_index(drop=True)
        sp = lambda z, c: z[c].corr(z.obs, method="spearman")  # noqa: E731
        diff = [sp(m.iloc[i], "sim_gps") - sp(m.iloc[i], "sim_base")
                for i in (rng.integers(0, len(m), len(m)) for _ in range(5000))]
        lr = lambda c: np.log10(m[c].clip(lower=1) / m.obs)  # noqa: E731
        res[str(year)] = {"detectors": int(len(m)), "spearman_base": float(sp(m, "sim_base")),
                          "spearman_gps": float(sp(m, "sim_gps")), "diff": float(sp(m, "sim_gps") - sp(m, "sim_base")),
                          "diff_ci95": np.percentile(diff, [2.5, 97.5]).tolist(), "p_diff_le_0": float(np.mean(np.array(diff) <= 0)),
                          "median_abs_log10_ratio_base": float(lr("sim_base").abs().median()),
                          "median_abs_log10_ratio_gps": float(lr("sim_gps").abs().median())}
    OUT.write_text(json.dumps(res, indent=2) + "\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
