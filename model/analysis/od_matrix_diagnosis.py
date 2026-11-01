#!/usr/bin/env python3
"""Where the full-matrix demand changes the volumes: calibration half only, Monday and Saturday. Diagnostic, selects nothing.

  python3 od_matrix_diagnosis.py -> model/results/demand/od_matrix_diagnosis.json
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calibrate_demand as C  # noqa: E402
import demand_scaling as D  # noqa: E402
import od_matrix as M  # noqa: E402
import detector_baselines as B  # noqa: E402

BINS = [0, 3000, 6000, 12000, 24000, 1e9]


def main():
    t = M.table("cal")
    t = pd.concat([t[t.day == d] for d in C.CAL_DAYS]).reset_index(drop=True)
    t["road_class"] = M.pd.Series(B.CLS.reindex(t.poly_lid).values)
    t["vol"] = pd.cut(t.obs, BINS).astype(str)
    out = {"rows": int(len(t))}
    runs = {"frozen": M.frozen_path} | {n: (lambda n: lambda d: M.base(n, d).parent)(n) for n in ("N100_r20_x", "N347_r20_x", "N100_r20", "N347_r20")}
    for n, p in runs.items():
        s = M.daily(p, t)
        lr = np.log10(np.clip(s, 1, None) / t.obs.values)
        g = lambda key: {str(k): {"n": int(len(v)), "median_log10": float(v.median()), "sd_log10": float(v.std())} for k, v in pd.Series(lr).groupby(t[key].values)}
        out[n] = {"by_road_class": g("road_class"), "by_observed_volume": g("vol"), "by_province": g("prov"), "share_below_half": float((lr < -np.log10(2)).mean()), "share_above_double": float((lr > np.log10(2)).mean())}
    (D.RES / "od_matrix_diagnosis.json").write_text(json.dumps(out, indent=1) + "\n")
    for n in runs:
        print(n, "below/above", round(out[n]["share_below_half"], 3), round(out[n]["share_above_double"], 3))
        for k in ("by_road_class", "by_observed_volume"):
            print("  ", {a: (b["n"], round(b["median_log10"], 2), round(b["sd_log10"], 2)) for a, b in out[n][k].items()})


if __name__ == "__main__":
    main()
