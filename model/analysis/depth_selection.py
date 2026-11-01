#!/usr/bin/env python3
"""Propagation depth of the correction estimated by cross-validation over detectors (Part B, step 3).

sensitivity_fixed.py compared depths 1, 3 and 5 on one 20% hold-out. Here the 2020 detectors that are complete
on each validation day are split in 5 folds; every fold is withheld in turn (together with the detectors
sharing its link), the correction is run with the remaining detectors for every depth 1..6, and the absolute
hourly error is measured on the withheld detectors (raw simulation vs corrected). Held-out detectors never
stop propagation. Pooled reduction (percentage points of the observed volume) per depth, with a bootstrap over
detectors (2000 resamples, seed 20261033). Rule fixed before looking at the data: the selected depth is the
smallest one whose reduction is within one bootstrap standard error of the best depth.

  python3 depth_selection.py run [DEPTHS [FOLDS]]     e.g. "1,3" "2" for a quick test; default 1..6 and all 5 folds
  python3 depth_selection.py summary
Output: model/results/corrected/depth_selection.csv (per detector, day, depth) and depth_selection.json
"""
import contextlib
import io
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reconstruct_and_validate as P  # noqa: E402

SEED, K, N_BOOT = 20261033, 5, 2000
DEPTHS = (1, 2, 3, 4, 5, 6)


def one_day(args):
    base, depths, nfolds = args
    sim = P.corrector(base)
    raw = pd.read_csv(sim.unique_file, sep=";")
    cols = [c for c in raw.columns if c.startswith("20")]
    day = pd.to_datetime(cols[0]).normalize()
    obs = P.coil_table_local(day.year)
    obs = obs[(obs.index >= day) & (obs.index < day + pd.Timedelta(days=1))]
    mapped = sorted(set(int(c.split("_")[0]) for c in sim.dfc.columns))
    complete = [c for c in mapped if all(f"{c}_{k}" in obs.columns for k in (0, 1))
                and len(obs) == 96 and obs[[f"{c}_0", f"{c}_1"]].notna().all().all()]
    perm = list(np.random.default_rng(SEED).permutation(complete))
    base_p2c = dict(sim.poly2coil)
    rows = []
    for f in range(nfolds):
        test = perm[f::K]
        test_links = {sim.coil2poly[c] for c in test}
        pool = [c for c in perm if c not in test and sim.coil2poly[c] not in test_links]
        others = [t for t in sim.dfb.tag.values if t not in complete and sim.coil2poly[t] not in test_links]
        for depth in depths:
            sim.recursion_max_depth = depth
            sim.poly2coil = {p: c for p, c in base_p2c.items() if p not in test_links}
            with contextlib.redirect_stdout(io.StringIO()):
                out = pd.read_csv(sim.correct(pool + others, suffix="depthsel"), sep=";")
            for c in test:
                pc = sim.coil2poly[c]
                err_raw = err = tot = 0.0
                for dc, ow in [("IN", "FT"), ("OUT", "TF")]:
                    if f"{c}_{dc}" not in sim.dfc.columns:
                        continue
                    o = sim.dfc[f"{c}_{dc}"].values.astype(float)
                    r = raw[(raw.poly_cid == pc) & (raw.oneway == ow)][cols].values.ravel().astype(float)
                    a = out[(out.poly_cid == pc) & (out.oneway == ow)][cols].values.ravel().astype(float)
                    if len(r) == 24 and len(a) == 24:
                        err_raw += np.abs(r - o).sum(); err += np.abs(a - o).sum(); tot += o.sum()
                if tot > 0:
                    rows.append(dict(day=str(day.date()), coil=int(c), fold=f, depth=depth, obs=tot,
                                     abs_raw=err_raw, abs_assim=err))
    return rows


def run(depths=DEPTHS, nfolds=K):
    bases = [b for b in P.basenames() if Path(b).name.startswith("sim_2002")]
    with ProcessPoolExecutor(min(len(bases), 8)) as ex:
        rows = [r for rs in ex.map(one_day, [(b, depths, nfolds) for b in bases]) for r in rs]
    pd.DataFrame(rows).to_csv(P.OUT / "depth_selection.csv", index=False)
    summary()


def summary():
    d = pd.read_csv(P.OUT / "depth_selection.csv")
    rng = np.random.default_rng(SEED)
    coils = d.coil.unique()
    g = {c: x for c, x in d.groupby("coil")}

    def red(sub):
        s = sub.groupby("depth")[["obs", "abs_raw", "abs_assim"]].sum()
        return 100 * (s.abs_raw - s.abs_assim) / s.obs
    base = red(d)
    boots = pd.DataFrame([red(pd.concat([g[c] for c in rng.choice(coils, len(coils))])) for _ in range(N_BOOT)])
    best = base.idxmax()
    se = boots[best].std()
    chosen = int(base.index[(base >= base.max() - se)].min())
    # paired differences from the selected depth, same resamples for both depths (reported, not part of the rule)
    diff = boots.sub(boots[chosen], axis=0)
    paired = {int(k): {"diff_pp": float(base[k] - base[chosen]), "ci95": [float(diff[k].quantile(0.025)), float(diff[k].quantile(0.975))]}
              for k in base.index if k != chosen}
    out = {"paired_vs_selected": paired,"detectors": int(len(coils)), "days": sorted(d.day.unique().tolist()),
           "reduction_pp": {int(k): float(v) for k, v in base.items()},
           "ci95": {int(k): [float(boots[k].quantile(0.025)), float(boots[k].quantile(0.975))] for k in base.index},
           "best_depth": int(best), "se_of_best": float(se), "selected_depth": chosen,
           "raw_error_pct": float(100 * d.drop_duplicates(["day", "coil"]).abs_raw.sum() / d.drop_duplicates(["day", "coil"]).obs.sum())}
    (P.OUT / "depth_selection.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    if sys.argv[1] == "summary":
        summary()
    else:
        dep = tuple(int(x) for x in sys.argv[2].split(",")) if len(sys.argv) > 2 else DEPTHS
        run(dep, int(sys.argv[3]) if len(sys.argv) > 3 else K)
