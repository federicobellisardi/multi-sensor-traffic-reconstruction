#!/usr/bin/env python3
"""Value of OD pairings at two endpoint radii, with the null D2. Protocol: model/results/experiments/PROTOCOL_OD_PAIRING_D2.md.

  python3 od_pairing_d2.py check          generator checks -> experiments/od_pairing_d2_check.json
  python3 od_pairing_d2.py controls       Monte Carlo and empirical controls -> experiments/od_pairing_d2_controls.json
  python3 od_pairing_d2.py jobs | one NAME DAY
  python3 od_pairing_d2.py evaluate       -> experiments/od_pairing_d2.json
Names: <r25|r10>_real_s<seed>, <r25|r10>_D2_<rep>. Outputs: $SIM_RUNS/od_pairing_d2/<name>/; r25 real runs come from od_pairing.
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
import od_matrix as M  # noqa: E402
import od_pairing as P  # noqa: E402
import source_value as V  # noqa: E402
from paths import RESULTS as R1  # noqa: E402

OUT = D.RUNS / "od_pairing_d2"
RES = R1 / "experiments"
GRID = {"r25": "N347_r20_x", "r10": "N347_r10_x"}  # the name r20 stands for the selected radius, 25 km
REPS = (0, 1, 2)
ENGINE_SEED = {0: 11, 1: 12, 2: 13}
BINS = np.arange(4.0, 101.0, 4.0)  # amendment 1; the registered 2 km failed G2 (od_pairing_d2_check_2km.json)
DAYS = C.CAL_DAYS
SEED, MC_SEED, BOOT_SEED, N_BOOT = 20261109, 20261112, 20261110, 2000
SWEEPS, MEAN_SWEEPS = 3000, 200  # the share moved saturates: 0.31 at 6,400 sweeps and 0.32 at 25,600 in a peak interval
RHO = (0.02, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5)
_real = {}


def names():
    return [f"{r}_real_s{s}" for r in GRID for s in (1, 2)] + [f"{r}_D2_{k}" for r in GRID for k in REPS]


def new_names():
    return [n for n in names() if not n.startswith("r25_real")]


def folder(name):
    if name.startswith("r25_real"):
        return P.OUT / f"N347_real_{name.split('_')[-1]}"
    return OUT / name


def base(name, day):
    return folder(name) / f"sim_{D.tag(day)}"


def done(name, day):
    return bool(list(folder(name).glob(f"sim_{D.tag(day)}_uniq_*.csv")))


def jobs():
    for n in new_names():
        for d in DAYS:
            if not done(n, d):
                print(n, d)


def real_config(radius, day, path):
    c, _ = M.config(GRID[radius], day, 1.0, path)
    c["sources"] = D.province_scaled(c["sources"])
    return c


def is_relation(s):
    return next(iter(s["pawns"])) == "scr_dest"


def geometry(src):
    keys = [k for k, s in src.items() if is_relation(s)]
    pts = {}
    for k in keys:
        for e in ("source_location", "dest_location"):
            pts.setdefault((src[k][e]["lat"], src[k][e]["lon"]), src[k][e])
    ids = {p: i for i, p in enumerate(pts)}
    xy = np.array(list(pts))
    dist = P.km(xy[:, None, :], xy[None, :, :])
    org = np.array([ids[(src[k]["source_location"]["lat"], src[k]["source_location"]["lon"])] for k in keys])
    dst = np.array([ids[(src[k]["dest_location"]["lat"], src[k]["dest_location"]["lon"])] for k in keys])
    rate = np.array([src[k]["creation_rate"] for k in keys])
    return keys, list(pts.values()), xy, dist, org, dst, rate


def permute_interval(o, d0, dist, cls, rng):
    """One interval: destinations exchanged within the distance bin of each agent, then swaps that close the gap in mean distance."""
    d, n = d0.copy(), len(d0)
    if n < 2:
        return d
    target = cls[o, d0]
    legal = lambda i, j: (d[i] != d[j]) & (o[i] != d[j]) & (o[j] != d[i]) & (cls[o[i], d[j]] == target[i]) & (cls[o[j], d[i]] == target[j])
    for _ in range(SWEEPS):
        i, j = P.pairs(n, rng)
        ok = legal(i, j)
        d[i[ok]], d[j[ok]] = d[j[ok]], d[i[ok]]
    want = dist[o, d0].sum()
    for _ in range(MEAN_SWEEPS):
        gap = dist[o, d].sum() - want
        if abs(gap) <= 0.002 * want:
            break
        i, j = P.pairs(n, rng)
        ok = np.where(legal(i, j))[0]
        gain = dist[o[i[ok]], d[j[ok]]] + dist[o[j[ok]], d[i[ok]]] - dist[o[i[ok]], d[i[ok]]] - dist[o[j[ok]], d[j[ok]]]
        use = ok[gain * gap < 0]
        gain = gain[gain * gap < 0]
        order = np.argsort(-np.abs(gain))
        use = use[order][np.cumsum(np.abs(gain[order])) <= abs(gap)]
        d[i[use]], d[j[use]] = d[j[use]], d[i[use]]
    return d


def permute(src, rep, day, radius):
    """D2 sources: same relation agents by interval, destinations exchanged. Other sources unchanged."""
    keys, loc, xy, dist, org, dst, rate = geometry(src)
    cls = np.digitize(dist, BINS)
    rng = np.random.default_rng([SEED, rep, DAYS.index(day)])
    template = src[keys[0]]
    new, moved, total = {}, 0, 0
    for q in range(rate.shape[1]):
        o, d0 = np.repeat(org, rate[:, q]), np.repeat(dst, rate[:, q])
        d = permute_interval(o, d0, dist, cls, rng)
        moved += int((d != d0).sum())
        total += len(d)
        if len(d):
            u, c = np.unique(np.column_stack([o, d]), axis=0, return_counts=True)
            for (i, j), v in zip(u, c):
                new.setdefault((int(i), int(j)), np.zeros(rate.shape[1], int))[q] = int(v)
    nodes = M.nodes() if radius == "r10" else None
    count = {}
    def small(i):
        if i not in count:
            count[i] = M.near(xy[i, 0], xy[i, 1], nodes, 10) >= M.MIN_NODES
        return count[i]
    out = {k: s for k, s in src.items() if k not in set(keys)}
    for (i, j), v in new.items():
        s = json.loads(json.dumps({a: b for a, b in template.items() if a != "creation_rate"}))
        s["pawns"]["scr_dest"].pop("cherry_pick", None)
        s["pawns"]["scr_dest"]["cherry_pick"] = "small" if radius == "r10" and small(i) and small(j) else "medium"
        s.update(source_location=loc[i], dest_location=loc[j], creation_rate=[int(x) for x in v])
        out[f"p{i}_{j}_IN"] = s
    return out, {"agents": total, "share_moved": moved / max(total, 1), "sources": len(new), "real_sources": len(keys)}


def config(name, day):
    radius, kind, rep = name.split("_")
    c = real_config(radius, day, base(name, day))
    if kind == "real":
        c["seed"] = int(rep[1:])
        return c, {}
    c["sources"], info = permute(c["sources"], int(rep), day, radius)
    c["seed"] = ENGINE_SEED[int(rep)]
    return c, info


def one(name, day):
    assert name in new_names(), name
    c, info = config(name, day)
    print(info, flush=True)
    res = D.run(c, base(name, day))
    print(*res, flush=True)
    sys.exit(1 if res[1] else 0)


def by_interval(src):
    """Origins and destinations by interval, and trips by interval and distance bin, of the relation sources."""
    keys, loc, xy, dist, org, dst, rate = geometry(src)
    pos = lambda i: (float(xy[i, 0]), float(xy[i, 1]))
    oo, dd, h, tot, w = {}, {}, {}, 0.0, 0.0
    cls = np.digitize(dist, BINS)
    for a, b, r in zip(org, dst, rate):
        oo[pos(a)] = oo.get(pos(a), 0) + r
        dd[pos(b)] = dd.get(pos(b), 0) + r
        h[int(cls[a, b])] = h.get(int(cls[a, b]), 0) + r
        w += dist[a, b] * r.sum()
        tot += r.sum()
    self_pairs = int((org == dst).sum())
    return oo, dd, h, w / tot, self_pairs, {str(k): v.tolist() for k, v in h.items()}


def same(a, b):
    return set(a) == set(b) and all((a[k] == b[k]).all() for k in a)


def check():
    res, ok = {}, True
    for day in DAYS:
        for radius in GRID:
            real = real_config(radius, day, base("x", day))
            ao, ad, ah, am, _, _ = by_interval(real["sources"])
            other = {k: s for k, s in real["sources"].items() if not is_relation(s)}
            for rep in REPS:
                c, info = permute(json.loads(json.dumps(real["sources"])), rep, day, radius)
                bo, bd, bh, bm, selfs, _ = by_interval(c)
                kinds = {}
                for s in c.values():
                    p = s["pawns"]["scr_dest"].get("cherry_pick") if is_relation(s) else None
                    if p:
                        kinds[p] = kinds.get(p, 0) + sum(s["creation_rate"])
                r = {**info, "origins_identical": same(ao, bo), "destinations_identical": same(ad, bd), "distance_bins_identical_by_interval": same(ah, bh),
                     "mean_km_real": am, "mean_km_null": bm, "mean_gap": bm / am - 1, "self_pairs": selfs, "other_sources_identical": all(c.get(k) == s for k, s in other.items()), "total_identical": sum(sum(s["creation_rate"]) for s in c.values()) == sum(sum(s["creation_rate"]) for s in real["sources"].values()), "agents_by_radius_key": kinds}
                r["G1"] = bool(r["origins_identical"] and r["destinations_identical"] and r["distance_bins_identical_by_interval"] and abs(r["mean_gap"]) <= 0.01 and not selfs and r["other_sources_identical"] and r["total_identical"])
                r["G2"] = r["share_moved"] >= 0.5
                ok &= r["G1"] and r["G2"]
                res[f"{day}_{radius}_{rep}"] = r
                print(day, radius, rep, {k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
    res["passed"] = bool(ok)
    (RES / "od_pairing_d2_check.json").write_text(json.dumps(res, indent=1) + "\n")
    print("passed", ok)


# ---------------------------------------------------------------- estimator
def table(real_paths, null_paths, sets=None):
    """Long table: one row per detector and comparison, log10 of obs, of each real run and each null run."""
    rows = []
    for day in DAYS:
        for setname, t in (sets(day) if sets else V.sets(day)).items():
            log = lambda p: np.log10(np.clip(V.daily(p, day, t.poly_lid), 1, None))
            reals = np.array([log(p) for p in real_paths])
            nulls = np.array([log(p) for p in null_paths])
            keep = (reals > 0).all(axis=0) & (nulls > 0).all(axis=0)
            rows.append({"comparison": f"{day}_{setname}", "coil": t.coil.values[keep], "obs": np.log10(t.obs.values[keep]), "reals": reals[:, keep], "nulls": nulls[:, keep]})
    return rows


def dm(x):
    return x - x.mean()


def terms(obs, reals, nulls):
    """Cross-fitted products by detector row: z.y and z.x, with noise of real and null independent between z and x, y."""
    zy, zx = np.zeros_like(obs), np.zeros_like(obs)
    for k in range(len(nulls)):
        other = np.delete(nulls, k, axis=0).mean(axis=0)
        for u in range(len(reals)):
            for v in range(len(reals)):
                if u == v and len(reals) > 1:
                    continue
                z, y, x = dm(reals[v] - nulls[k]), dm(obs - other), dm(reals[u] - other)
                zy += z * y
                zx += z * x
    return zy, zx


def by_detector(rows, obs_of=None):
    frames = []
    for r in rows:
        obs = r["obs"] if obs_of is None else obs_of(r)
        zy, zx = terms(obs, r["reals"], r["nulls"])
        frames.append(pd.DataFrame({"coil": r["coil"], "zy": zy, "zx": zx}))
    return pd.concat(frames).groupby("coil").sum()


def estimate(g, rng, n_boot=N_BOOT):
    w = rng.multinomial(len(g), np.ones(len(g)) / len(g), size=n_boot)
    den = w @ g.zx.values
    with np.errstate(divide="ignore", invalid="ignore"):
        boots = (w @ g.zy.values) / den
    return float(g.zy.sum() / g.zx.sum()), [float(x) for x in np.nanpercentile(boots, [2.5, 97.5])]


def spread(rows):
    """Signal tau, from the product of independent real and null differences; sigma, residual of obs on the mean real; both pooled."""
    products, residual, seed = [], [], []
    for r in rows:
        n = len(r["nulls"])
        for u in range(len(r["reals"])):
            for v in range(len(r["reals"])):
                if u == v:
                    continue
                for k in range(n):
                    for j in range(n):
                        if j != k:
                            products.append(np.sum(dm(r["reals"][u] - r["nulls"][k]) * dm(r["reals"][v] - r["nulls"][j])))
        residual.append(dm(r["obs"] - r["reals"].mean(axis=0)))
        seed.append(dm(r["reals"][0] - r["reals"][-1]))
    size = sum(len(r["obs"]) for r in rows)
    tau2 = np.sum(products) / (size * len(products) / len(rows))
    sigma = float(np.concatenate(residual).std())
    return float(np.sqrt(max(tau2, 0.0))), sigma, float(np.concatenate(seed).std() / np.sqrt(2))


def matrix(rows, values):
    """Detectors by comparisons, NaN where the detector is not in the comparison."""
    coils = sorted({c for r in rows for c in r["coil"]})
    m = pd.DataFrame(np.nan, index=coils, columns=[r["comparison"] for r in rows])
    for r in rows:
        m.loc[r["coil"], r["comparison"]] = values(r)
    return m


def donate(m, rng):
    """Vectors moved to another detector, so that the correlation within a detector stays and the link to the original road goes."""
    v = m.values
    fill = np.nanmean(v, axis=1, keepdims=True)
    full = np.where(np.isnan(v), fill, v)
    return full[rng.permutation(len(v))]


def monte_carlo(rows, rho, truth, n_rep, rng, n_boot=500):
    """Repeats the estimator on synthetic data with the structure, residuals and noise of `rows`. Returns shares and median b."""
    shape = matrix(rows, lambda r: dm(r["reals"].mean(axis=0) - r["nulls"].mean(axis=0)))
    shape /= np.nanstd(shape.values)
    res = matrix(rows, lambda r: dm(r["obs"] - r["reals"].mean(axis=0)))
    sigma = np.nanstd(res.values)
    seed = np.concatenate([(r["reals"][0] - r["reals"][-1]) / np.sqrt(2) for r in rows])
    perm = np.concatenate([(r["nulls"][k] - np.delete(r["nulls"], k, axis=0).mean(axis=0)) * np.sqrt(2 / 3) for r in rows for k in range(len(r["nulls"]))])
    seed, perm = seed - seed.mean(), perm - perm.mean()
    mask = ~np.isnan(shape.values)
    bs, excl0, cover1, excl1_incl0, incl0_excl1 = [], 0, 0, 0, 0
    for _ in range(n_rep):
        s = donate(shape, rng) * rho * sigma
        e = donate(res, rng)
        syn = []
        for c, r in enumerate(rows):
            m = mask[:, c]
            coil = shape.index[m].values
            n = m.sum()
            noise = lambda pool, size: rng.choice(pool, size=size)
            reals = np.array([s[m, c] + noise(seed, n) for _ in r["reals"]])
            nulls = np.array([noise(perm, n) for _ in r["nulls"]])
            syn.append({"coil": coil, "obs": truth * s[m, c] + e[m, c], "reals": reals, "nulls": nulls})
        b, (lo, hi) = estimate(by_detector(syn), rng, n_boot)
        bs.append(b)
        excl0 += lo > 0 or hi < 0
        cover1 += lo <= 1 <= hi
        excl1_incl0 += (lo > 1 or hi < 1) and lo <= 0 <= hi
        incl0_excl1 += (lo > 0 or hi < 0) and lo <= 1 <= hi
    return {"rho": rho, "truth": truth, "median_b": float(np.median(bs)), "excludes_0": excl0 / n_rep, "covers_1": cover1 / n_rep, "correct_decision": (incl0_excl1 if truth == 1 else excl1_incl0) / n_rep}


def rule_power(rows, rho, rng, n_rep=400):
    """Power of the classification: lower of the correct decision when b = 1 and when b = 0."""
    a, b = monte_carlo(rows, rho, 1.0, n_rep, rng), monte_carlo(rows, rho, 0.0, n_rep, rng)
    return {"b1": a, "b0": b, "power": min(a["correct_decision"], b["correct_decision"])}


def empirical_controls(rows, rng, n_rep=500):
    """Truth from a simulated run plus residuals moved to other detectors: a real seed, or a null rep."""
    res = matrix(rows, lambda r: dm(r["obs"] - r["reals"].mean(axis=0)))
    out = {}
    for lab, want in (("truth_real", 1.0), ("truth_null", 0.0)):
        bs, excl0, cover1 = [], 0, 0
        for _ in range(n_rep):
            e = pd.DataFrame(donate(res, rng), index=res.index, columns=res.columns)
            syn = []
            for r in rows:
                noise = e.loc[r["coil"], r["comparison"]].values
                if want:
                    syn.append({**r, "obs": r["reals"][0] + noise, "reals": r["reals"][1:]})  # one real left: its noise is shared by x and z, a small attenuation
                else:
                    syn.append({**r, "obs": r["nulls"][0] + noise, "nulls": r["nulls"][1:]})
            b, (lo, hi) = estimate(by_detector(syn), rng, 500)
            bs.append(b)
            excl0 += lo > 0 or hi < 0
            cover1 += lo <= 1 <= hi
        out[lab] = {"expected": want, "median_b": float(np.median(bs)), "excludes_0": excl0 / n_rep, "covers_1": cover1 / n_rep}
    return out


def controls():
    rng = np.random.default_rng(MC_SEED)
    old = lambda n: P.OUT / n
    rows = table([old("N347_real_s1"), old("N347_real_s2")], [old(f"N347_D_{k}") for k in REPS])
    tau, sigma, seed = spread(rows)
    res = {"template": "N347 at 25 km with the earlier null D", "tau_signal": tau, "sigma": sigma, "seed_noise": seed, "rho_template": tau / sigma, "detectors": len({c for r in rows for c in r["coil"]}), "rows": sum(len(r["coil"]) for r in rows), "grid": []}
    for rho in RHO:
        p = rule_power(rows, rho, rng)
        res["grid"].append(p)
        print(rho, {k: round(p["b1"][k], 3) for k in ("median_b", "excludes_0", "covers_1", "correct_decision")}, {k: round(p["b0"][k], 3) for k in ("median_b", "excludes_0", "covers_1", "correct_decision")}, "power", p["power"], flush=True)
    high = [p for p in res["grid"] if p["b1"]["rho"] >= 0.2]
    res["E1"] = all(abs(p["b0"]["median_b"]) <= 0.2 and p["b0"]["excludes_0"] <= 0.10 for p in high)
    res["E2"] = all(abs(p["b1"]["median_b"] - 1) <= 0.2 and p["b1"]["covers_1"] >= 0.90 for p in high)
    res["E3"] = any(p["power"] >= 0.8 for p in res["grid"])
    res["rho_needed"] = next((p["b1"]["rho"] for p in res["grid"] if p["power"] >= 0.8), None)
    res["power_at_template"] = rule_power(rows, tau / sigma, rng)
    res["empirical"] = empirical_controls(rows, rng)
    res["passed"] = bool(res["E1"] and res["E2"] and res["E3"])
    (RES / "od_pairing_d2_controls.json").write_text(json.dumps(res, indent=1, default=float) + "\n")
    print(json.dumps({k: v for k, v in res.items() if k != "grid"}, indent=1, default=float))


# ---------------------------------------------------------------- evaluation
def classify(lo, hi, power):
    if power < 0.8:
        return "inconclusive (power below 80%)"
    has0, has1 = lo <= 0 <= hi, lo <= 1 <= hi
    return {(False, True): "supported", (True, False): "unsupported", (True, True): "inconclusive", (False, False): "anomalous, treated as inconclusive"}[(has0, has1)]


def analyse(rows, rng):
    tau, sigma, seed = spread(rows)
    b, ci = estimate(by_detector(rows), rng)
    p = rule_power(rows, tau / sigma, np.random.default_rng(MC_SEED + 1))
    return {"detectors": len({c for r in rows for c in r["coil"]}), "rows": sum(len(r["coil"]) for r in rows), "b": b, "ci95": ci, "tau_signal": tau, "sigma": sigma, "seed_noise": seed, "rho": tau / sigma, "power": p, "classification": classify(*ci, p["power"])}


def secondary(rows, rng):
    out = {}
    for r in rows:
        o, s, n = r["obs"], r["reals"][0], r["nulls"]
        stat = lambda a, i: ((o[i] - a[i]).std(), spearmanr(o[i], a[i])[0])
        size = len(o)
        idx = [rng.integers(0, size, size) for _ in range(N_BOOT)]
        d = np.array([np.subtract(stat(s, i), np.mean([stat(a, i) for a in n], axis=0)) for i in idx])
        every = np.arange(size)
        out[r["comparison"]] = {"n": size, "sd_real": stat(s, every)[0], "spearman_real": stat(s, every)[1], "sd_null": float(np.mean([stat(a, every)[0] for a in n])), "spearman_null": float(np.mean([stat(a, every)[1] for a in n])), "sd_diff_ci95": P.ci(d[:, 0]), "spearman_diff_ci95": P.ci(d[:, 1]), "volume_ratio": float((10 ** s).sum() / (10 ** o).sum()), "median_sensitivity": float(np.median(np.abs(s - n.mean(axis=0))))}
    return out


def all_links(radius, day):
    link = lambda name: D.link_daily(next(folder(name).glob(f"sim_{D.tag(day)}_uniq_*.csv")))
    real = link(f"{radius}_real_s1")
    nulls = pd.concat([link(f"{radius}_D2_{k}") for k in REPS], axis=1).reindex(real.index).fillna(0).mean(axis=1)
    ok = (real > 0) & (nulls > 0)
    return float(np.median(np.abs(np.log10(real[ok] / nulls[ok]))))


def evaluate():
    rng = np.random.default_rng(BOOT_SEED)
    res = {}
    for radius in GRID:
        rows = table([folder(f"{radius}_real_s{s}") for s in (1, 2)], [folder(f"{radius}_D2_{k}") for k in REPS])
        a = analyse(rows, rng)
        a["secondary"] = secondary(rows, rng)
        a["all_links_median_abs_log10"] = {d: all_links(radius, d) for d in DAYS}
        a["empirical_controls"] = empirical_controls(rows, np.random.default_rng(MC_SEED + 2))
        res[radius] = a
        print(radius, json.dumps({k: v for k, v in a.items() if k not in ("power", "secondary")}, default=float), "power", a["power"]["power"], flush=True)
    (RES / "od_pairing_d2.json").write_text(json.dumps(res, indent=1, default=float) + "\n")


if __name__ == "__main__":
    {"check": check, "controls": controls, "jobs": jobs, "evaluate": evaluate}[sys.argv[1]]() if len(sys.argv) == 2 else one(sys.argv[2], sys.argv[3])
