#!/usr/bin/env python3
"""Province factors for shorter walks, step 1c of results/experiments/PROTOCOL_OD_ROUTING.md.

  python3 od_length_factors.py jobs STAGE      missing simulations; STAGE is grid or a round number
  python3 od_length_factors.py one ARM DAY     run one simulation -> $SIM_RUNS/od_length_factors/ARM/
  python3 od_length_factors.py select          k by day type -> selected_k.json
  python3 od_length_factors.py factors ROUND   factors of the round -> factors_roundROUND.json
  python3 od_length_factors.py evaluate        -> results/experiments/od_length_factors.json
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
import demand_scaling as D  # noqa: E402
import od_length as L  # noqa: E402
import province_demand as PD  # noqa: E402
import source_value as V  # noqa: E402
from paths import RESULTS as R1  # noqa: E402

OUT = D.RUNS / "od_length_factors"
DAYS = L.DAYS
TTB = 1800
GRID = (1.5, 2.0, 2.5, 3.0, 3.5)
BOOT_SEED, N_BOOT = 20261106, 2000


def base(arm, day):
    return OUT / arm / f"sim_{D.tag(day)}"


def done(arm, day):
    return bool(list(base(arm, day).parent.glob(f"sim_{D.tag(day)}_uniq_*.csv")))


def selected():
    return json.load(open(OUT / "selected_k.json"))


def config(arm, day):
    if arm.startswith("k"):
        k, f = float(arm[1:]), None
    else:
        k, f = selected()[day]["k"], json.load(open(OUT / f"factors_{arm}.json"))
    src = D.scaled_sources(day, {x: k for x in D.CLASSES})
    for s in src.values():
        if f:
            ends = [f[p] for p in (PD.prov_of(s[e]) for e in ("source_location", "dest_location") if e in s) if p]
            if ends:
                g = float(np.prod(ends)) ** (1 / len(ends))
                s["creation_rate"] = [int(round(g * v)) for v in s["creation_rate"]]
    c = D.v6_config(day, D.VARIANTS["V6_scaled"], src, base(arm, day))
    for s in c["sources"].values():
        p = next(iter(s["pawns"].values()))
        if "TTB" in p:
            p["TTB"] = TTB
    return c


def jobs(stage):
    arms = [f"k{k}" for k in GRID] if stage == "grid" else [f"round{stage}"]
    for a in arms:
        for d in DAYS:
            if not done(a, d):
                print(a, d)


def one(arm, day):
    res = D.run(config(arm, day), base(arm, day))
    print(*res, flush=True)
    sys.exit(1 if res[1] else 0)


def select():
    out = {}
    for d in DAYS:
        t = L.sets(d)["calibration"]
        loss = {k: float(np.mean(np.log10(np.clip(V.daily(OUT / f"k{k}", d, t.poly_lid), 1, None) / t.obs.values) ** 2)) for k in GRID}
        k = min(loss, key=loss.get)
        out[d] = {"k": k, "loss": loss, "at_edge": k in (GRID[0], GRID[-1])}
    (OUT / "selected_k.json").write_text(json.dumps(out, indent=1) + "\n")
    print(out)


def factors(rnd):
    sel, r = selected(), []
    arm = lambda d: f"k{sel[d]['k']}" if rnd == 1 else f"round{rnd - 1}"
    for d in DAYS:
        t = L.sets(d)["calibration"]
        r.append(pd.Series(np.log10(np.clip(V.daily(OUT / arm(d), d, t.poly_lid), 1, None) / t.obs.values), index=t.coil.values))
    r = pd.concat(r)
    med = r.groupby(PD.PROV.reindex(r.index).values).median()
    prev = json.load(open(OUT / f"factors_round{rnd - 1}.json")) if rnd > 1 else {p: 1.0 for p in PD.X.CODE.values()}
    new = {p: float(np.clip(prev[p] * 10 ** (-med.get(p, 0.0)), 0.5, 2.5)) for p in prev}
    (OUT / f"factors_round{rnd}.json").write_text(json.dumps(new, indent=1) + "\n")
    print(new)


def evaluate():
    rng = np.random.default_rng(BOOT_SEED)
    sel = selected()
    res = {"selected_k": sel, "factors": json.load(open(OUT / "factors_round2.json"))}
    for d in DAYS:
        res[d] = {}
        for s, t in L.sets(d).items():
            o, f, m = t.obs.values, V.daily(OUT / "round2", d, t.poly_lid), V.daily(D.OUT / "V6_scaled", d, t.poly_lid)
            x = {"arm": L.metrics(f, o), "model": L.metrics(m, o)}
            ok = (f > 0) & (m > 0)
            a, b, c = np.log10(f[ok] / o[ok]), np.log10(m[ok] / o[ok]), o[ok]
            idx = [rng.integers(0, len(c), len(c)) for _ in range(N_BOOT)]
            x["dispersion_minus_model_ci95"] = np.percentile([a[i].std() - b[i].std() for i in idx], [2.5, 97.5]).tolist()
            x["spearman_minus_model_ci95"] = np.percentile([spearmanr(c[i], f[ok][i])[0] - spearmanr(c[i], m[ok][i])[0] for i in idx], [2.5, 97.5]).tolist()
            res[d][s] = x
    mean = lambda s, a, q: float(np.mean([res[d][s][a][q] for d in DAYS]))
    edge = any(sel[d]["at_edge"] for d in DAYS)
    res["rule"] = {"dispersion": mean("dev_test", "arm", "dispersion"), "model_dispersion": mean("dev_test", "model", "dispersion"), "ratio": mean("dev_test", "arm", "ratio"), "at_edge": edge}
    res["rule"]["holds"] = bool(res["rule"]["dispersion"] < res["rule"]["model_dispersion"] and 0.9 <= res["rule"]["ratio"] <= 1.1 and not edge)
    (R1 / "experiments/od_length_factors.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res["rule"], indent=1))


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "jobs":
        jobs(a[1])
    elif a[0] == "one":
        one(a[1], a[2])
    elif a[0] == "factors":
        factors(int(a[1]))
    else:
        {"select": select, "evaluate": evaluate}[a[0]]()
