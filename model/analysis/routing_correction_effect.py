#!/usr/bin/env python3
"""Paired comparison of the two route-choice configurations before and after the coil correction.

Unit: directed link with GPS reference counts (per-link hourly-profile error, mae_pp, in percentage
points of daily flow; tables written by reconstruct_and_validate.py validate). Compared quantities, for
every campaign (all days), on the links present in both runs:
  * V6 - V0 of the raw simulation and of the corrected simulation (negative = V6 better);
  * raw - corrected for V0 and for V6 (positive = the correction helps).
Statistic: median of the paired per-link difference; 95% percentile bootstrap over links
(5,000 resamples, seed 20261030) and share of links where the first term is smaller.
Usage: python3 model/analysis/routing_correction_effect.py
Output: model/results/corrected/routing_correction_effect.json
"""
import json

import numpy as np
import pandas as pd

from paths import RESULTS as R1

N_BOOT, SEED = 5000, 20261030
FILES = {"V6": R1 / "private", "V0": R1 / "private/baseline_v0"}


def table(run, year):
    return pd.read_csv(FILES[run] / f"corrected_link_metrics_{year}_all.csv", index_col=0)


def paired(d, rng):
    """Median of a paired difference, bootstrap interval, share of negative and positive links."""
    d = d.dropna().values
    ix = rng.integers(0, len(d), size=(N_BOOT, len(d)))
    med = np.median(d[ix], axis=1)
    return {"n_links": int(len(d)), "median_pp": float(np.median(d)),
            "ci95_pp": [float(np.quantile(med, 0.025)), float(np.quantile(med, 0.975))],
            "share_negative": float((d < 0).mean()), "share_positive": float((d > 0).mean())}


def main():
    rng = np.random.default_rng(SEED)
    out = {"bootstrap_resamples": N_BOOT, "seed": SEED}
    for year in (2020, 2021):
        a, b = table("V6", year), table("V0", year)
        idx = a.index.intersection(b.index)
        a, b = a.loc[idx], b.loc[idx]
        out[str(year)] = {
            "median_mae_pp": {"V6_raw": float(a.mae_pp_raw.median()), "V6_corrected": float(a.mae_pp.median()),
                              "V0_raw": float(b.mae_pp_raw.median()), "V0_corrected": float(b.mae_pp.median())},
            "V6_minus_V0_raw": paired(a.mae_pp_raw - b.mae_pp_raw, rng),
            "V6_minus_V0_corrected": paired(a.mae_pp - b.mae_pp, rng),
            "correction_gain_V6": paired(a.mae_pp_raw - a.mae_pp, rng),
            "correction_gain_V0": paired(b.mae_pp_raw - b.mae_pp, rng),
        }
    (R1 / "corrected/routing_correction_effect.json").write_text(json.dumps(out, indent=1) + "\n")
    for y in ("2020", "2021"):
        print(y, out[y]["median_mae_pp"])
        for k in ("V6_minus_V0_raw", "V6_minus_V0_corrected", "correction_gain_V6", "correction_gain_V0"):
            r = out[y][k]
            print(f"  {k:24s} n={r['n_links']} median={r['median_pp']:+.3f} CI=[{r['ci95_pp'][0]:+.3f},{r['ci95_pp'][1]:+.3f}]"
                  f" neg={r['share_negative']:.2f} pos={r['share_positive']:.2f}")


if __name__ == "__main__":
    main()
