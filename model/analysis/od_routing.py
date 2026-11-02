#!/usr/bin/env python3
"""Routing of OD pairs at N347 (results/experiments/PROTOCOL_OD_ROUTING.md).

  python3 od_routing.py jobs                list missing simulations
  python3 od_routing.py one ARM DAY         run one simulation -> $SIM_RUNS/od_routing/ARM/
  python3 od_routing.py evaluate            -> results/experiments/od_routing.json
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
import demand_scaling as D  # noqa: E402
import od_pairing as P  # noqa: E402
import source_value as V  # noqa: E402
from paths import RESULTS as R1  # noqa: E402

OUT = D.RUNS / "od_routing"
DAYS = ("2020-02-10", "2020-02-15")
WEIGHTS = ((1.0, 0.0), (0.0, 1.0), (0.25, 0.0), (0.5, 0.25))
ARMS = {"multi4": (True, None, 1), "miss10": (False, 0.10, 1), "miss30": (False, 0.30, 1), "multi4_miss10": (True, 0.10, 1), "multi4_s2": (True, None, 2)}
SPLIT_SEED, BOOT_SEED, N_BOOT = 20261103, 20261104, 2000


def base(arm, day):
    return OUT / arm / f"sim_{D.tag(day)}"


def share(rate, n):
    """Equal shares of each interval over n types; the remainder rotates, so each total is exact."""
    out = [[] for _ in range(n)]
    for t, r in enumerate(rate):
        q, m = divmod(int(r), n)
        for i in range(n):
            out[i].append(q + (1 if (i + t) % n < m else 0))
    return out


def config(arm, day):
    multi, miss, seed = ARMS[arm]
    c = P.real_config("N347", day, base(arm, day))
    c["seed"] = seed
    new = {}
    for key, s in c["sources"].items():
        if next(iter(s["pawns"])) != "scr_dest":
            new[key] = s
            continue
        par = s["pawns"]["scr_dest"]
        if miss is not None:
            par = dict(par, beta_bp_miss=miss)
        if not multi:
            new[key] = dict(s, pawns={"scr_dest": par})
            continue
        for i, (rate, (a, a_s)) in enumerate(zip(share(s["creation_rate"], len(WEIGHTS)), WEIGHTS)):
            if sum(rate):
                new[f"t{i}_{key}"] = dict(s, creation_rate=rate, pawns={f"scr_dest_{i}": dict(par, alpha_we=a, alpha_speed=a_s)})
    total = lambda x: sum(sum(v["creation_rate"]) for v in x.values())
    assert total(new) == total(c["sources"])
    c["sources"] = new
    return c


def jobs():
    for arm in ARMS:
        for day in DAYS:
            if not list(base(arm, day).parent.glob(f"sim_{D.tag(day)}_uniq_*.csv")):
                print(arm, day)


def one(arm, day):
    res = D.run(config(arm, day), base(arm, day))
    print(*res, flush=True)
    sys.exit(1 if res[1] else 0)


def development(day):
    """Calibration half and half of the test half, by province; the other half of the test half is blind."""
    g = D.group_observations()
    u = g.drop_duplicates("coil").reset_index(drop=True)
    cal = set(u.coil[V.E.split(u)])
    rng = np.random.default_rng(SPLIT_SEED)
    test = u[~u.coil.isin(cal)].sort_values("coil")
    blind = set()
    prov = "prov" if "prov" in test else "province"
    for _, h in test.groupby(prov):
        blind |= set(rng.permutation(h.coil.values)[: len(h) // 2 + (rng.random() < 0.5 and len(h) % 2)])
    return {"2020": g[(g.day == day) & ~g.coil.isin(blind)][["coil", "poly_lid", "obs"]].reset_index(drop=True),
            "2021": (lambda t: t[~t.coil.isin(blind)].reset_index(drop=True))(V.later_obs(V.LATER[day]))}, sorted(int(b) for b in blind)


def metrics(s, o):
    m = s > 0
    lr = np.log10(s[m] / o[m])
    c = lr - np.median(lr)
    q = np.percentile(lr, [25, 75])
    return {"n": int(len(o)), "zero_flow": int((~m).sum()), "low_tail": float(np.mean(c < -np.log10(2))), "high_tail": float(np.mean(c > np.log10(2))), "spearman": float(spearmanr(o, s)[0]),
            "robust_spread": float((q[1] - q[0]) / 1.349), "dispersion": float(lr.std()), "median_abs_log10": float(np.median(np.abs(c))), "ratio": float(s.sum() / o.sum())}


def evaluate():
    folders = {"real": P.OUT / "N347_real_s1", "model": D.OUT / "V6_scaled", **{a: OUT / a for a in ARMS}}
    rng = np.random.default_rng(BOOT_SEED)
    res = {}
    for day in DAYS:
        sets, blind = development(day)
        res["blind_detectors"] = blind
        for year, t in sets.items():
            o = t.obs.values
            flows = {a: V.daily(p, day, t.poly_lid) for a, p in folders.items()}
            r = {a: metrics(f, o) for a, f in flows.items()}
            for a in ARMS:
                idx = [rng.integers(0, len(o), len(o)) for _ in range(N_BOOT)]
                d = np.array([[metrics(flows[a][i], o[i])[k] - metrics(flows["real"][i], o[i])[k] for k in ("low_tail", "spearman", "robust_spread", "dispersion")] for i in idx])
                r[a]["minus_real_ci95"] = dict(zip(("low_tail", "spearman", "robust_spread", "dispersion"), np.percentile(d, [2.5, 97.5], axis=0).T.tolist()))
            res[f"{day}_{year}"] = r
    res["rule"] = {a: {"mean_low_tail_2020": float(np.mean([res[f"{d}_2020"][a]["low_tail"] for d in DAYS])), "mean_spearman_2020_minus_real": float(np.mean([res[f"{d}_2020"][a]["spearman"] - res[f"{d}_2020"]["real"]["spearman"] for d in DAYS]))} for a in ("real", "model", *ARMS)}
    (R1 / "experiments/od_routing.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res["rule"], indent=1))


if __name__ == "__main__":
    {"jobs": jobs, "evaluate": evaluate}[sys.argv[1]]() if len(sys.argv) == 2 else one(sys.argv[2], sys.argv[3])
