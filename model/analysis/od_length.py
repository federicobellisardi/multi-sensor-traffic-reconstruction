#!/usr/bin/env python3
"""Trip length and demand scale, step 1b of results/experiments/PROTOCOL_OD_ROUTING.md.

  python3 od_length.py jobs            list missing simulations
  python3 od_length.py one ARM DAY     run one simulation -> $SIM_RUNS/od_length/ARM/
  python3 od_length.py evaluate        -> results/experiments/od_length.json
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
import demand_scaling as D  # noqa: E402
import od_matrix as M  # noqa: E402
import od_routing as O  # noqa: E402
import source_value as V  # noqa: E402
from paths import RESULTS as R1  # noqa: E402

OUT = D.RUNS / "od_length"
DAYS = O.DAYS
GRID = {(900, 25): (2.0, 2.5, 3.0, 3.5, 4.0, 5.0), (900, 10): (2.0, 2.5, 3.0, 3.5, 4.0, 5.0), (1800, 25): (2.0, 2.5, 3.0)}
BOOT_SEED, N_BOOT = 20261105, 2000


def arm(ttb, r, k):
    return f"t{ttb}_r{r}_k{k}"


def parse(name):
    t, r, k = name.split("_")
    return int(t[1:]), int(r[1:]), float(k[1:])


def base(name, day):
    return OUT / name / f"sim_{D.tag(day)}"


def config(name, day):
    ttb, r, k = parse(name)
    src = D.province_scaled(D.scaled_sources(day, {x: k for x in D.CLASSES}))
    c = D.v6_config(day, D.VARIANTS["V6_scaled"], src, base(name, day))
    xy = M.nodes() if r < 25 else None
    if xy is not None:
        c["cherry_pick_mode"]["small"] = float(r)
    for s in c["sources"].values():
        t = next(iter(s["pawns"]))
        p = s["pawns"][t]
        if "TTB" in p:
            p["TTB"] = ttb
        elif xy is not None and t == "scr_dest":
            a, b = s["source_location"], s["dest_location"]
            if min(M.near(a["lat"], a["lon"], xy, r), M.near(b["lat"], b["lon"], xy, r)) >= M.MIN_NODES:
                p["cherry_pick"] = "small"
    return c


def names():
    return [arm(t, r, k) for (t, r), ks in GRID.items() for k in ks]


def jobs():
    for n in names():
        for d in DAYS:
            if not list(base(n, d).parent.glob(f"sim_{D.tag(d)}_uniq_*.csv")):
                print(n, d)


def one(name, day):
    res = D.run(config(name, day), base(name, day))
    print(*res, flush=True)
    sys.exit(1 if res[1] else 0)


def metrics(s, o):
    m = s > 0
    lr = np.log10(s[m] / o[m])
    q = np.percentile(lr, [25, 75])
    return {"n": int(len(o)), "zero_flow": int((~m).sum()), "ratio": float(s.sum() / o.sum()), "spearman": float(spearmanr(o, s)[0]), "dispersion": float(lr.std()), "robust_spread": float((q[1] - q[0]) / 1.349),
            "median_abs_log10": float(np.median(np.abs(lr))), "within_factor2": float(np.mean(np.abs(lr) < np.log10(2))), "low_tail": float(np.mean(lr - np.median(lr) < -np.log10(2)))}


def sets(day):
    dev, _ = O.development(day)
    g, t21 = dev["2020"], dev["2021"]
    u = D.group_observations().drop_duplicates("coil").reset_index(drop=True)
    cal = set(u.coil[V.E.split(u)])
    return {"calibration": g[g.coil.isin(cal)].reset_index(drop=True), "dev_test": g[~g.coil.isin(cal)].reset_index(drop=True), "2021": t21}


def evaluate():
    rng = np.random.default_rng(BOOT_SEED)
    res, rule = {"model": {}}, {}
    for day in DAYS:
        S = sets(day)
        flow = lambda p, t: V.daily(p, day, t.poly_lid)
        ref = {s: flow(D.OUT / "V6_scaled", t) for s, t in S.items()}
        res["model"][day] = {s: metrics(ref[s], S[s].obs.values) for s in S}
        for key, ks in GRID.items():
            name = f"t{key[0]}_r{key[1]}"
            cal = S["calibration"]
            loss = {k: float(np.mean(np.log10(np.clip(flow(OUT / arm(*key, k), cal), 1, None) / cal.obs.values) ** 2)) for k in ks}
            best = min(loss, key=loss.get)
            r = {"loss": loss, "selected": best, "at_edge": best in (ks[0], ks[-1])}
            for s, t in S.items():
                o, f = t.obs.values, flow(OUT / arm(*key, best), t)
                r[s] = metrics(f, o)
                both = (f > 0) & (ref[s] > 0)
                a, b, c = np.log10(f[both] / o[both]), np.log10(ref[s][both] / o[both]), o[both]
                idx = [rng.integers(0, len(c), len(c)) for _ in range(N_BOOT)]
                r[s]["dispersion_minus_model_ci95"] = np.percentile([a[i].std() - b[i].std() for i in idx], [2.5, 97.5]).tolist()
                r[s]["spearman_minus_model_ci95"] = np.percentile([spearmanr(c[i], f[both][i])[0] - spearmanr(c[i], ref[s][both][i])[0] for i in idx], [2.5, 97.5]).tolist()
            res.setdefault(name, {})[day] = r
    for name in [n for n in res if n != "model"]:
        x = res[name]
        sd = float(np.mean([x[d]["dev_test"]["dispersion"] for d in DAYS]))
        ref = float(np.mean([res["model"][d]["dev_test"]["dispersion"] for d in DAYS]))
        ratio = float(np.mean([x[d]["dev_test"]["ratio"] for d in DAYS]))
        edge = any(x[d]["at_edge"] for d in DAYS)
        rule[name] = {"dispersion": sd, "model_dispersion": ref, "ratio": ratio, "at_edge": edge, "holds": bool(sd < ref and 0.9 <= ratio <= 1.1 and not edge)}
    res["rule"] = rule
    (R1 / "experiments/od_length.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(rule, indent=1))


if __name__ == "__main__":
    {"jobs": jobs, "evaluate": evaluate}[sys.argv[1]]() if len(sys.argv) == 2 else one(sys.argv[2], sys.argv[3])
