#!/usr/bin/env python3
"""Hourly-share validation against GPS, separated where GPS also enters the model.

Route-choice weights come from Forli-Cesena and the variant was selected there on 10 Feb 2020, so the links of that
province are not independent of the route choice; outside it they are, and 2021 is a later season. Medians of the link
MAE (pp) and paired differences, bootstrap over links (spatially correlated, so intervals are optimistic). Validation
only: nothing in the frozen model changes on this.

  python3 gps_validation_split.py -> model/results/corrected/gps_validation_split.json
"""
import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import ROOT  # noqa: E402

N_BOOT, SEED = 2000, 20261043
PRIV = ROOT / "model/results/private"
OUT = ROOT / "model/results/corrected"
PAIRS = {"corrected_minus_raw": ("mae_pp", "mae_pp_raw"), "corrected_minus_mts": ("mae_pp", "mae_pp_mts"), "corrected_minus_od": ("mae_pp", "mae_pp_od"),
         "raw_minus_mts": ("mae_pp_raw", "mae_pp_mts"), "raw_minus_od": ("mae_pp_raw", "mae_pp_od")}


def fc_links():
    g = gpd.read_file(ROOT / "model/results/carto_a059fb0.geojson").to_crs(32632)
    prov = gpd.read_file(ROOT / "vars/extra/er-shapes.geojson").to_crs(32632)
    fc = prov[prov.PRO_NAME.str.startswith("Forl")].union_all()
    return set(g.poly_cid[g.geometry.representative_point().within(fc)].astype(int))


def block(m, rng):
    res = {"links": int(len(m)), **{c: float(m[c].median()) for c in ("mae_pp", "mae_pp_raw", "mae_pp_mts", "mae_pp_od", "mae_pp_flat", "pearson")}}
    a = {}
    for k, (x, y) in PAIRS.items():
        d = (m[x] - m[y]).values
        b = [np.median(d[rng.integers(0, len(d), len(d))]) for _ in range(N_BOOT)]
        a[k] = {"median_pp": float(np.median(d)), "ci95_pp": [float(q) for q in np.percentile(b, [2.5, 97.5])], "share_negative": float((d < 0).mean())}
    res["paired"] = a
    return res


def main():
    fc = fc_links()
    rng = np.random.default_rng(SEED)
    out = {}
    for y in (2020, 2021):
        out[str(y)] = {}
        for kind in ("all", "weekday", "weekend"):
            m = pd.read_csv(PRIV / f"corrected_link_metrics_{y}_{kind}.csv", index_col=0).dropna(subset=list({v for p in PAIRS.values() for v in p}))
            inside = m.index.isin(fc)
            out[str(y)][kind] = {"forli_cesena": block(m[inside], rng), "rest_of_region": block(m[~inside], rng)}
    (OUT / "gps_validation_split.json").write_text(json.dumps(out, indent=1) + "\n")
    for y, a in out.items():
        for kind, b in a.items():
            for w, c in b.items():
                print(y, kind, w, c["links"], *(round(c[k], 2) for k in ("mae_pp", "mae_pp_raw", "mae_pp_mts", "mae_pp_od", "mae_pp_flat", "pearson")), {k: [round(v["median_pp"], 3)] + [round(q, 3) for q in v["ci95_pp"]] for k, v in c["paired"].items()})


if __name__ == "__main__":
    main()
