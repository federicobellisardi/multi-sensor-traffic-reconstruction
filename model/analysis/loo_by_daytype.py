#!/usr/bin/env python3
"""Leave-one-detector-out error by day type, from corrected/loo_detectors.csv (weekdays against Saturday and Sunday).

Pooled hourly absolute error as a share of the observed volume; 95% bootstrap over detectors of the reduction.

  python3 loo_by_daytype.py -> model/results/corrected/loo_by_daytype.json
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "model/results/corrected"
N_BOOT, SEED = 2000, 20261037


def summary(z, rng):
    by = z.groupby("coil")[["obs_total", "raw_abs", "loo_abs"]].sum()
    boot = []
    for _ in range(N_BOOT):
        b = by.iloc[rng.integers(0, len(by), len(by))]
        boot.append(100 * (b.raw_abs.sum() - b.loo_abs.sum()) / b.obs_total.sum())
    return {"days": int(z.day.nunique()), "coils": int(len(by)),
            "raw_error_pct": float(100 * by.raw_abs.sum() / by.obs_total.sum()),
            "loo_error_pct": float(100 * by.loo_abs.sum() / by.obs_total.sum()),
            "reduction_pp": float(100 * (by.raw_abs.sum() - by.loo_abs.sum()) / by.obs_total.sum()),
            "ci95_pp": [float(x) for x in np.percentile(boot, [2.5, 97.5])],
            "share_improved": float((by.loo_abs < by.raw_abs - 1e-9).mean()),
            "share_worse": float((by.loo_abs > by.raw_abs + 1e-9).mean())}


def main():
    d = pd.read_csv(OUT / "loo_detectors.csv").dropna(subset=["raw_abs", "loo_abs"])
    t = pd.to_datetime(d.day)
    d["year"], d["type"] = t.dt.year, np.where(t.dt.day_of_week >= 5, "weekend", "weekday")
    rng = np.random.default_rng(SEED)
    out = {str(y): {k: summary(z, rng) for k, z in g.groupby("type")} for y, g in d.groupby("year")}
    (OUT / "loo_by_daytype.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
