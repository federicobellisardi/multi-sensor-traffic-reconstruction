#!/usr/bin/env python3
"""Daily volumes of 2021 without the detectors of the calibration half, which enter the 141 detectors of the 2021 tests.

  python3 independent_2021.py -> model/results/experiments/independent_2021.json
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
import demand_scaling as D  # noqa: E402
import demand_scan_eval as E  # noqa: E402
from paths import RESULTS as R1  # noqa: E402

N_BOOT, SEED = 5000, 20261103


def stats(s, o):
    m = s > 0
    return {"n": int(len(o)), "ratio": float(s.sum() / o.sum()), "spearman": float(spearmanr(o, s)[0]), "dispersion": float(np.log10(s[m] / o[m]).std()),
            "median_abs_log10": float(np.median(np.abs(np.log10(np.clip(s, 1, None) / o)))), "within_factor2": float(np.mean(np.abs(np.log10(np.clip(s, 1, None) / o)) < np.log10(2)))}


def main():
    rng = np.random.default_rng(SEED)
    g = D.group_observations().drop_duplicates("coil").reset_index(drop=True)
    cal = set(g.coil[E.split(g)])
    l = pd.read_csv(R1 / "corrected/loo_detectors.csv").dropna(subset=["raw_total"])
    l = l[l.day.str.startswith("2021")].groupby(["coil", "day"])[["obs_total", "raw_total"]].sum().groupby("coil").mean()
    res = {"calibration_half": int(len(cal))}
    for name, t in (("all", l), ("without_calibration", l[~l.index.isin(cal)])):
        s, o = t.raw_total.values, t.obs_total.values
        r = stats(s, o)
        b = [stats(s[i], o[i]) for i in (rng.integers(0, len(o), len(o)) for _ in range(N_BOOT))]
        for k in ("ratio", "spearman", "median_abs_log10", "within_factor2"):
            r[k + "_ci95"] = np.percentile([x[k] for x in b], [2.5, 97.5]).tolist()
        res[name] = r
    (R1 / "experiments/independent_2021.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
