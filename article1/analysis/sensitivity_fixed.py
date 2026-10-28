#!/usr/bin/env python3
"""Sensitivity of the corrected assimilation to detector coverage and propagation depth.

For each 2020 validation day: detectors with complete local-day data in both directions are
split once (seed 20261027) into a fixed test set (20 %) and a training pool. Training subsets
contain 25, 50 or 100 % of the pool (three random draws for the partial subsets); the depth
limit is 1, 3 or 5 links. Test detectors are never assimilated and never stop propagation.
Output: article1/results/corrected/sensitivity_coverage_depth.csv and summary JSON.
"""
import contextlib
import io
import itertools
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reconstruct_and_validate as P  # noqa: E402

SEED = 20261027
FRACS, DEPTHS, DRAWS = (0.25, 0.5, 1.0), (1, 3, 5), 3


def one_day(base):
    sim = P.corrector(base)
    raw = pd.read_csv(sim.unique_file, sep=";")
    cols = [c for c in raw.columns if c.startswith("20")]
    day = pd.to_datetime(cols[0]).normalize()
    obs = P.coil_table_local(day.year)
    obs = obs[(obs.index >= day) & (obs.index < day + pd.Timedelta(days=1))]
    mapped = sorted(set(int(c.split("_")[0]) for c in sim.dfc.columns))
    complete = [c for c in mapped if all(f"{c}_{k}" in obs.columns for k in (0, 1))
                and len(obs) == 96 and obs[[f"{c}_0", f"{c}_1"]].notna().all().all()]
    rng = np.random.default_rng(SEED)
    perm = list(rng.permutation(complete))
    ntest = max(1, round(0.2 * len(perm)))
    test = perm[:ntest]
    test_links = {sim.coil2poly[c] for c in test}  # co-located detectors are held out with the test coil
    pool = [c for c in perm[ntest:] if sim.coil2poly[c] not in test_links]
    others = [t for t in sim.dfb.tag.values if t not in complete and sim.coil2poly[t] not in test_links]  # detectors without complete data stay as in the full run
    base_p2c = dict(sim.poly2coil)
    rows = []
    for frac, depth, draw in itertools.product(FRACS, DEPTHS, range(DRAWS)):
        if frac == 1.0 and draw > 0:
            continue
        k = max(1, round(frac * len(pool)))
        train = list(np.random.default_rng(SEED + draw).permutation(pool)[:k])
        sim.recursion_max_depth = depth
        sim.poly2coil = {p: c for p, c in base_p2c.items() if p not in test_links}
        with contextlib.redirect_stdout(io.StringIO()):
            out = pd.read_csv(sim.correct(train + others, suffix="sensitivity"), sep=";")
        err_raw = err = tot = 0.0
        for c in test:
            pc = sim.coil2poly[c]
            for dc, ow in [("IN", "FT"), ("OUT", "TF")]:
                if f"{c}_{dc}" not in sim.dfc.columns:
                    continue
                o = sim.dfc[f"{c}_{dc}"].values.astype(float)
                r = raw[(raw.poly_cid == pc) & (raw.oneway == ow)][cols].values.ravel().astype(float)
                a = out[(out.poly_cid == pc) & (out.oneway == ow)][cols].values.ravel().astype(float)
                if len(r) == 24 and len(a) == 24:
                    err_raw += np.abs(r - o).sum(); err += np.abs(a - o).sum(); tot += o.sum()
        rows.append(dict(day=str(day.date()), frac=frac, depth=depth, draw=draw, n_test=len(test), n_train=k,
                         obs=tot, abs_raw=err_raw, abs_assim=err))
    return rows


def main():
    bases = [b for b in P.basenames() if Path(b).name.startswith("sim_2002")]
    with ProcessPoolExecutor(4) as ex:
        rows = [r for rs in ex.map(one_day, bases) for r in rs]
    d = pd.DataFrame(rows)
    d.to_csv(P.OUT / "sensitivity_coverage_depth.csv", index=False)
    g = d.groupby(["frac", "depth", "draw"])[["obs", "abs_raw", "abs_assim"]].sum()
    g["reduction_pp"] = 100 * (g.abs_raw - g.abs_assim) / g.obs
    s = g.groupby(["frac", "depth"]).reduction_pp.agg(["mean", "min", "max"]).reset_index()
    s["raw_error_pct"] = float(100 * g.abs_raw.iloc[0] / g.obs.iloc[0])
    s.to_csv(P.OUT / "sensitivity_coverage_depth_summary.csv", index=False)
    print(s.to_string())


if __name__ == "__main__":
    main()
