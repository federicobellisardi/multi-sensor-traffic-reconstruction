#!/usr/bin/env python3
"""Daily volumes of the raw (or assimilated) reconstruction against all MTS detectors.

For every detector with complete local-day data in both directions, the observed daily count is
compared with the simulated daily count on its polyline (both directions). Outputs Spearman rank
correlation, share within a factor of two, volume ratio overall and by observed-volume tercile,
and the same statistics restricted to detectors outside the province of Forli-Cesena.
Usage: volume_check.py SIM_DIR campaign(2020|2021) [raw|assim]
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

A1 = Path(__file__).resolve().parents[1]
ROOT = A1.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))


def coil_table(year):
    import reconstruct_and_validate as P
    return P.coil_table_local(year)


def run(sim_dir, year, kind="raw"):
    days = pd.date_range("2020-02-10", "2020-02-17") if year == 2020 else pd.date_range("2021-06-28", "2021-07-04")
    bar = pd.read_csv(ROOT / "vars/extra/er_barriers_cartodata.csv", sep=";")
    prov = pd.read_csv(ROOT / "vars/extra/er_barriers.csv", sep=";").set_index("ID").PRO
    obs = coil_table(year)
    rows = []
    for d in days:
        t = f"{d:%y%m%d}"
        f = Path(sim_dir) / f"sim_{t}_uniq_{t}_000000.csv"
        s = pd.read_csv(str(f) + (".corrected" if kind == "assim" else ""), sep=";")
        cols = [c for c in s if c.startswith("20")]
        sv = s.groupby("poly_lid")[cols].sum().sum(axis=1)
        z = obs[obs.index.normalize() == d]
        for tag, lid in bar[["tag", "poly_lid"]].values:
            cc = [f"{tag}_0", f"{tag}_1"]
            if all(c in z for c in cc) and len(z) == 96 and z[cc].notna().all().all():
                rows.append((tag, prov.get(tag, ""), z[cc].sum().sum(), sv.get(lid, 0.0)))
    r = pd.DataFrame(rows, columns=["coil", "prov", "obs", "sim"]).groupby(["coil", "prov"]).mean().reset_index()
    r = r[r.obs > 0]

    def stats(x):
        lr = np.log10(x.sim.clip(lower=1) / x.obs)
        terc = pd.qcut(x.obs, 3, labels=["low", "mid", "high"])
        return dict(n=int(len(x)), spearman=float(x.sim.corr(x.obs, method="spearman")),
                    within_factor2=float((lr.abs() < np.log10(2)).mean()),
                    volume_ratio=float(x.sim.sum() / x.obs.sum()), median_log10_ratio=float(lr.median()),
                    ratio_by_tercile={k: float((x.sim / x.obs)[terc == k].median()) for k in ["low", "mid", "high"]})
    return {"all": stats(r), "outside_FC": stats(r[r.prov != "FO"])}, r


if __name__ == "__main__":
    out, _ = run(sys.argv[1], int(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else "raw")
    print(json.dumps(out, indent=1))
