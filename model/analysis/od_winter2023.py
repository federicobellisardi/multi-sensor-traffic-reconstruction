#!/usr/bin/env python3
"""Winter 2023 detectors against the raw frozen model, supplementary temporal comparison. Protocol: model/results/experiments/PROTOCOL_2023_WINTER.md.

  python3 od_winter2023.py frozen  -> model/results/experiments/winter2023.json
  python3 od_winter2023.py pairing -> model/results/experiments/winter2023_pairing.json (needs the runs of od_pairing_d2.py)
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calibrate_demand as C  # noqa: E402
import demand_scaling as D  # noqa: E402
import demand_scan_eval as E  # noqa: E402
import od_pairing_d2 as X  # noqa: E402
import source_value as V  # noqa: E402
from paths import RESULTS as R1  # noqa: E402

RES = R1 / "experiments"
FILE = D.ROOT / "data/coils_ave_230101-000000_231231-234500.csv"
WD = {C.CAL_DAYS[0]: "Mon", C.CAL_DAYS[1]: "Sat"}
SEED, N_BOOT = 20261111, 2000


def winter(day):
    """Complete detectors of the winter 2023 table for this day type, with the poly_lid of the detector."""
    f = pd.read_csv(FILE, sep=";")
    z = f[(f.wday == WD[day]) & (f.season == "winter")]
    assert len(z) == 96
    bar = pd.read_csv(D.ROOT / "vars/extra/er_barriers_cartodata.csv", sep=";").drop_duplicates("tag")
    rows = [(int(c), int(l), float(z[[f"{c}_0", f"{c}_1"]].sum().sum())) for c, l in bar[["tag", "poly_lid"]].values
            if f"{c}_0" in z and f"{c}_1" in z and z[[f"{c}_0", f"{c}_1"]].notna().all().all() and z[[f"{c}_0", f"{c}_1"]].sum().sum() > 0]
    return pd.DataFrame(rows, columns=["coil", "poly_lid", "obs"])


def groups():
    g = D.group_observations()
    u = g.drop_duplicates("coil").reset_index(drop=True)
    cal = set(u.coil[E.split(u)])
    exposed = (set(g.coil) - cal) | {c for d in V.LATER.values() for c in V.later_obs(d).coil}
    return cal, exposed


def metrics(s, o, rng):
    m = s > 0
    lr = np.log10(s[m] / o[m])
    base = {"n": len(o), "zero_flow": int((~m).sum()), "spearman": float(spearmanr(o, s)[0]), "sd_log10": float(lr.std()), "median_abs_log10": float(np.median(np.abs(np.log10(np.clip(s, 1, None) / o)))),
            "within_factor2": float(np.mean(np.abs(np.log10(np.clip(s, 1, None) / o)) < np.log10(2))), "volume_ratio_descriptive": float(s.sum() / o.sum())}
    idx = [rng.integers(0, len(o), len(o)) for _ in range(N_BOOT)]
    base["spearman_ci95"] = [float(x) for x in np.percentile([spearmanr(o[i], s[i])[0] for i in idx], [2.5, 97.5])]
    base["sd_log10_ci95"] = [float(x) for x in np.percentile([np.log10(s[i][s[i] > 0] / o[i][s[i] > 0]).std() for i in idx], [2.5, 97.5])]
    return base


def frozen():
    rng = np.random.default_rng(SEED)
    cal, exposed = groups()
    res = {"calibration_detectors": len(cal)}
    for day in C.CAL_DAYS:
        t = winter(day)
        t = t[~t.coil.isin(cal)].reset_index(drop=True)
        s = V.daily(D.OUT / "V6_scaled", day, t.poly_lid)
        part = {"A_all_outside_calibration": np.ones(len(t), bool), "B_exposed": t.coil.isin(exposed).values, "C_not_in_2020_or_2021_sets": ~t.coil.isin(exposed).values}
        res[day] = {k: metrics(s[m], t.obs.values[m], rng) for k, m in part.items()}
        ctx = {}
        for name, q in V.sets(day).items():
            common = q[q.coil.isin(t.coil)].reset_index(drop=True)
            sim = V.daily(D.OUT / "V6_scaled", day, common.poly_lid)
            o23 = common.coil.map(t.set_index("coil").obs).values
            ctx[name] = {"observed_that_period": metrics(sim, common.obs.values, rng), "observed_winter_2023": metrics(sim, o23, rng), "median_log10_2023_over_that_period": float(np.median(np.log10(o23 / common.obs.values)))}
        res[day]["context_descriptive"] = ctx
    (RES / "winter2023.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))


def pairing():
    cal, _ = groups()
    def sets(day):
        t = winter(day)
        return {"winter2023": t[~t.coil.isin(cal)].reset_index(drop=True)}
    rng = np.random.default_rng(SEED + 1)
    res = {}
    for radius in X.GRID:
        rows = X.table([X.folder(f"{radius}_real_s{s}") for s in (1, 2)], [X.folder(f"{radius}_D2_{k}") for k in X.REPS], sets)
        res[radius] = X.analyse(rows, rng)
    (RES / "winter2023_pairing.json").write_text(json.dumps(res, indent=1, default=float) + "\n")
    print(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    {"frozen": frozen, "pairing": pairing}[sys.argv[1]]()
