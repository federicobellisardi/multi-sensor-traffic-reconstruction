#!/usr/bin/env python3
"""Value of OD pairings with origin and destination marginals preserved. Protocol: model/results/experiments/PROTOCOL_OD_PAIRING.md.

  python3 od_pairing.py jobs | one NAME DAY | check | evaluate -> model/results/experiments/od_pairing.json
Names: <cov>_real_s<seed>, <cov>_<M|D>_<rep>, with cov N50 or N347. Outputs: $SIM_RUNS/od_pairing/<name>/.
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
import gps_validation_split as G  # noqa: E402
import od_matrix as M  # noqa: E402
import source_value as V  # noqa: E402
from paths import ROOT, RESULTS as R1  # noqa: E402

OUT = D.RUNS / "od_pairing"
RES = R1 / "experiments"
COV = {"N50": "N50_r20_x", "N347": "N347_r20_x"}
BINS = np.array([5.0, 10.0, 20.0, 50.0])
DAYS = C.CAL_DAYS
SEED, N_BOOT = 20261060, 2000
SWEEPS = 1000
ci = lambda v: [float(x) for x in np.nanpercentile(v, [2.5, 97.5])]


def names():
    out = [f"{c}_real_s{s}" for c in COV for s in (1, 2)]
    # null M at N347 (about 89,000 sources) ends with a segmentation fault, see the protocol
    return out + [f"{c}_{n}_{r}" for c in COV for n in "MD" for r in range(3) if not (D.NO_CODE and c == "N347" and n == "M")]


def base(name, day):
    return OUT / name / f"sim_{D.tag(day)}"


def done(name, day):
    return bool(list(base(name, day).parent.glob(f"sim_{D.tag(day)}_uniq_*.csv")))


def jobs():
    for n in names():
        for d in DAYS:
            if not done(n, d):
                print(n, d)


def real_config(cov, day, path):
    c, _ = M.config(COV[cov], day, 1.0, path)
    c["sources"] = D.province_scaled(c["sources"])
    return c


def km(a, b):
    la, lo, lb, lp = map(np.radians, (a[..., 0], a[..., 1], b[..., 0], b[..., 1]))
    return 2 * 6371 * np.arcsin(np.sqrt(np.sin((lb - la) / 2) ** 2 + np.cos(la) * np.cos(lb) * np.sin((lp - lo) / 2) ** 2))


def pairs(n, rng):
    """Disjoint random pairs of agents, so that a swap never touches an agent twice."""
    p = rng.permutation(n)
    return p[:n // 2], p[n // 2:n // 2 * 2]


def permute(src, kind, rng):
    """New municipal relation sources: per interval, destinations exchanged among agents. Origin and destination totals are exact."""
    rel = {k: s for k, s in src.items() if next(iter(s["pawns"])) == "scr_dest"}
    keys = list(rel)
    pts = {}
    for s in rel.values():
        for e in ("source_location", "dest_location"):
            pts.setdefault((s[e]["lat"], s[e]["lon"]), s[e])
    ids = {p: i for i, p in enumerate(pts)}
    xy = np.array(list(pts))
    dist = km(xy[:, None, :], xy[None, :, :])
    cls = np.digitize(dist, BINS)
    org = np.array([ids[(rel[k]["source_location"]["lat"], rel[k]["source_location"]["lon"])] for k in keys])
    dst = np.array([ids[(rel[k]["dest_location"]["lat"], rel[k]["dest_location"]["lon"])] for k in keys])
    rate = np.array([rel[k]["creation_rate"] for k in keys])
    template = rel[keys[0]]
    new = {}
    moved = total = 0
    for q in range(rate.shape[1]):
        o, d = np.repeat(org, rate[:, q]), np.repeat(dst, rate[:, q])
        d0, n = d.copy(), len(d)
        if n < 2:
            pass
        elif kind == "M":
            d = rng.permutation(d)
            for _ in range(50):
                i, j = pairs(n, rng)
                bad = (o[i] == d[i]) | (o[j] == d[j])
                ok = bad & (o[i] != d[j]) & (o[j] != d[i])
                d[i[ok]], d[j[ok]] = d[j[ok]], d[i[ok]]
                if not (o == d).any():
                    break
            assert not (o == d).any()
        else:
            target = cls[o, d0]
            for _ in range(SWEEPS):
                i, j = pairs(n, rng)
                ok = (d[i] != d[j]) & (o[i] != d[j]) & (o[j] != d[i]) & (cls[o[i], d[j]] == target[i]) & (cls[o[j], d[i]] == target[j])
                d[i[ok]], d[j[ok]] = d[j[ok]], d[i[ok]]
        moved += int((d != d0).sum())
        total += n
        u, c = np.unique(np.column_stack([o, d]), axis=0, return_counts=True) if n else (np.empty((0, 2), int), [])
        for (i, j), v in zip(u, c):
            new.setdefault((int(i), int(j)), np.zeros(rate.shape[1], int))[q] = int(v)
    loc = list(pts.values())
    out = {k: s for k, s in src.items() if k not in rel}
    for (i, j), v in new.items():
        s = json.loads(json.dumps({a: b for a, b in template.items() if a != "creation_rate"}))
        s.update(source_location=loc[i], dest_location=loc[j], creation_rate=[int(x) for x in v])
        out[f"p{i}_{j}_IN"] = s
    return out, {"agents": total, "share_moved": moved / max(total, 1), "sources": len(new), "real_sources": len(keys)}


def config(name, day):
    cov, kind, rep = name.split("_")
    c = real_config(cov, day, base(name, day))
    if kind == "real":
        c["seed"] = int(rep[1:])
        return c, {}
    rng = np.random.default_rng([SEED, list(COV).index(cov), "MD".index(kind), int(rep), DAYS.index(day)])
    c["sources"], info = permute(c["sources"], kind, rng)
    return c, info


def margins(src):
    o, d, t = {}, {}, 0
    for s in src.values():
        if next(iter(s["pawns"])) != "scr_dest":
            continue
        r = np.array(s["creation_rate"])
        a, b = (s["source_location"]["lat"], s["source_location"]["lon"]), (s["dest_location"]["lat"], s["dest_location"]["lon"])
        o[a] = o.get(a, 0) + r
        d[b] = d.get(b, 0) + r
    return o, d


def distance_bins(src):
    h = np.zeros(5)
    w = tot = 0.0
    for s in src.values():
        if next(iter(s["pawns"])) != "scr_dest":
            continue
        a = np.array([s["source_location"]["lat"], s["source_location"]["lon"]])
        b = np.array([s["dest_location"]["lat"], s["dest_location"]["lon"]])
        x, n = float(km(a, b)), sum(s["creation_rate"])
        h[np.digitize(x, BINS)] += n
        w += x * n
        tot += n
    return (h / tot).round(4).tolist(), round(w / tot, 2)


def check():
    res = {}
    for cov in COV:
        for day in DAYS:
            real = real_config(cov, day, base("x", day))
            ao, ad = margins(real["sources"])
            total = lambda c: sum(sum(s["creation_rate"]) for s in c.values())
            res[f"{cov}_{day}"] = {"real": {"agents": total(real["sources"]), "distance": distance_bins(real["sources"])}}
            for kind in "MD":
                c, info = config(f"{cov}_{kind}_0", day)
                bo, bd = margins(c["sources"])
                same = all((ao[k] == bo[k]).all() for k in ao) and all((ad[k] == bd[k]).all() for k in ad) and set(ao) == set(bo) and set(ad) == set(bd)
                res[f"{cov}_{day}"][kind] = {**info, "margins_identical": bool(same), "total_identical": total(c["sources"]) == total(real["sources"]), "distance": distance_bins(c["sources"])}
    RES.mkdir(exist_ok=True)
    (RES / "od_pairing_check.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))


def one(name, day):
    c, _ = config(name, day)
    res = D.run(c, base(name, day))
    print(*res, flush=True)
    sys.exit(1 if res[1] else 0)


def stats(s, o):
    m = s > 0
    return np.log10(s[m] / o[m]).std(), spearmanr(o, s)[0]


def evaluate():
    rng = np.random.default_rng(SEED + 1)
    res = {}
    fc = G.fc_links()
    keep = set(pd.read_csv(R1 / "private/gps_links_unchanged.csv", index_col=0).query("hausdorff_m <= 1").index)
    v = pd.read_csv(ROOT / "work_viasat/viasat_20200210_20200218_timed_fluxes.csv", sep=";", parse_dates=["time"])
    v = v[v.cid.isin(keep)]
    for cov in COV:
        res[cov] = {}
        for day in DAYS:
            res[cov][day] = {}
            path = lambda n: OUT / n
            kinds = [k for k in "MD" if done(f"{cov}_{k}_0", day)]
            rows = {}
            for setname, t in V.sets(day).items():
                o = t.obs.values
                x = {n: V.daily(path(n), day, t.poly_lid) for n in names() if n.startswith(cov + "_") and done(n, day)}
                real, real2 = x[f"{cov}_real_s1"], x[f"{cov}_real_s2"]
                out = {"n": len(o), "real": dict(zip(("sd", "spearman"), stats(real, o))), "seed_difference": dict(zip(("sd", "spearman"), np.subtract(stats(real2, o), stats(real, o))))}
                idx = [rng.integers(0, len(o), len(o)) for _ in range(N_BOOT)]
                for kind in kinds:
                    nu = [x[f"{cov}_{kind}_{r}"] for r in range(3)]
                    point = np.array([stats(a, o) for a in nu])
                    dif = np.array([np.subtract(stats(real[i], o[i]), np.mean([stats(a[i], o[i]) for a in nu], axis=0)) for i in idx])
                    tw = np.array([np.subtract(stats(real2[i], real[i]), np.mean([stats(a[i], real[i]) for a in nu], axis=0)) for i in idx])
                    pos = (real > 0) & (nu[0] > 0)
                    out[kind] = {"null_mean": dict(zip(("sd", "spearman"), point.mean(axis=0))), "between_permutations_range": dict(zip(("sd", "spearman"), np.ptp(point, axis=0))),
                                 "real_minus_null_sd_ci95": ci(dif[:, 0]), "real_minus_null_spearman_ci95": ci(dif[:, 1]),
                                 "sensitivity_median_abs_log10": float(np.median(np.abs(np.log10(real[pos] / nu[0][pos])))),
                                 "twin_sd_ci95": ci(tw[:, 0]), "twin_spearman_ci95": ci(tw[:, 1])}
                sens = np.abs(np.log10(np.clip(real, 1, None) / np.clip(np.mean([x[f"{cov}_{kinds[0]}_{r}"] for r in range(3)], axis=0), 1, None)))
                top = sens >= np.quantile(sens, 0.75)
                out["top_sensitive_quartile"] = {"n": int(top.sum()), "median_sensitivity": float(np.median(sens[top])), **{k: {"real": dict(zip(("sd", "spearman"), stats(real[top], o[top]))), "null": dict(zip(("sd", "spearman"), np.mean([stats(x[f"{cov}_{k}_{r}"][top], o[top]) for r in range(3)], axis=0)))} for k in kinds}}
                rows[setname] = out
            g = v[v.time.dt.date == pd.Timestamp(day).date()].groupby("cid").total_fluxes.sum()
            g = g[g > 0]
            link = lambda n: (lambda u: u.groupby("poly_cid")[[c for c in u if c.startswith("20")]].sum().sum(axis=1))(pd.read_csv(next((OUT / n).glob(f"sim_{D.tag(day)}_uniq_*.csv")), sep=";"))
            real_link = link(f"{cov}_real_s1")
            gps = {}
            for lab, mask in (("FC", g.index.isin(fc)), ("elsewhere", ~g.index.isin(fc))):
                q = g[mask]
                gps[lab] = {"links": len(q), "real": float(spearmanr(q, real_link.reindex(q.index).fillna(0))[0])}
                for kind in kinds:
                    gps[lab][kind] = float(np.mean([spearmanr(q, link(f"{cov}_{kind}_{r}").reindex(q.index).fillna(0))[0] for r in range(3)]))
            rows["gps"] = gps
            all_m = link(f"{cov}_{kinds[0]}_0").reindex(real_link.index).fillna(0)
            ok = (real_link > 0) & (all_m > 0)
            rows["sensitivity_arm"] = kinds[0]
            rows["all_links_sensitivity"] = float(np.median(np.abs(np.log10(real_link[ok] / all_m[ok]))))
            res[cov][day] = rows
    (RES / "od_pairing.json").write_text(json.dumps(res, indent=1, default=float) + "\n")
    print("written")


if __name__ == "__main__":
    {"jobs": jobs, "check": check, "evaluate": evaluate}[sys.argv[1]]() if len(sys.argv) == 2 else one(sys.argv[2], sys.argv[3])
