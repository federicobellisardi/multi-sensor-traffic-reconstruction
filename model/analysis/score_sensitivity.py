#!/usr/bin/env python3
"""Sensitivity of the simulated volumes to the node scores of the random origins/destinations.

Compares the population scores (build_node_scores.py) with uniform scores, at the k of k_choice.json, on the two
calibration days of calibrate_demand.py. Reference: the grid run of calibrate_demand.py at the same k.
Rule fixed before the runs: sd of log10(sim/obs) on the calibration detectors; the population hypothesis is supported
only if the paired bootstrap interval (over detectors) of sd(uniform) - sd(population) is entirely above zero. The
error by province uses every detector with data on the two days: it is a diagnostic and chooses nothing.

  python3 score_sensitivity.py jobs         list the simulations (name, day) not yet done
  python3 score_sensitivity.py one uniform DAY   one simulation (cluster job)
  python3 score_sensitivity.py check DAY    differences between the configuration and the reference run
  python3 score_sensitivity.py evaluate     -> model/results/demand/score_sensitivity.json
Outputs of the simulations: $SIM_RUNS/score_sensitivity/uniform/
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calibrate_demand as C  # noqa: E402
import demand_scaling as D  # noqa: E402
import demand_scan_eval as E  # noqa: E402
import reconstruct_and_validate as P  # noqa: E402

BASE = D.RUNS / "score_sensitivity"
UNIFORM = BASE / "node_score_uniform.csv"
N_BOOT, SEED = 2000, 20261034


def k_final():
    return json.load(open(D.RES / "k_choice.json"))["k"]


def reference(day):
    return C.basename(f"k{k_final():.1f}", day)


def basename(day):
    return BASE / "uniform" / f"sim_{D.tag(day)}"


def uniform_scores():
    """Same nodes and format as the population file, with score 1 everywhere."""
    BASE.mkdir(parents=True, exist_ok=True)
    s = pd.read_csv(D.ROOT / "vars/extra/node_score_pop2021.csv", sep=";")
    s["score"] = 1.0
    s.to_csv(UNIFORM, sep=";", index=False)


def config(day):
    base = basename(day)
    cfg = D.v6_config(day, D.VARIANTS["V6_scaled"], D.scaled_sources(day, {c: k_final() for c in D.CLASSES}), base)
    cfg["file_score_pop"] = str(UNIFORM)
    return cfg, base


def jobs():
    for day in C.CAL_DAYS:
        if not list(basename(day).parent.glob(f"sim_{D.tag(day)}_uniq_*.csv")):
            print("uniform", day)


def one(_name, day):
    uniform_scores()
    cfg, base = config(day)
    res = D.run(cfg, base)
    print(*res, flush=True)
    sys.exit(1 if res[1] else 0)


def check(day):
    cfg, _ = config(day)
    ref = json.load(open(reference(day).parent / f"{reference(day).name}.json"))
    cfg, ref = json.loads(json.dumps(cfg)), ref
    print("differences:", [k for k in sorted(set(cfg) | set(ref)) if cfg.get(k) != ref.get(k)])


def sd(r):
    return float(np.std(r))


def evaluate():
    P.prepare_coils()
    o = D.observations()
    o = o[o.day.isin(C.CAL_DAYS)].reset_index(drop=True)
    o10 = o[o.day == "2020-02-10"].reset_index(drop=True)
    calib = set(o10.coil[E.split(o10)])
    flows = {}
    for day in C.CAL_DAYS:
        flows["population", day] = D.link_daily(next(reference(day).parent.glob(f"sim_{D.tag(day)}_uniq_*.csv")))
        flows["uniform", day] = D.link_daily(next(basename(day).parent.glob(f"sim_{D.tag(day)}_uniq_*.csv")))
    for n in ("population", "uniform"):
        sim = np.array([flows[n, d].get(l, 0.0) for d, l in o[["day", "poly_lid"]].values])
        o[n] = np.log10(np.clip(sim, 1, None) / o.obs.values)
    z = o[o.coil.isin(calib)].reset_index(drop=True)
    coils = z.coil.unique()
    by = {c: np.where(z.coil.values == c)[0] for c in coils}
    rng = np.random.default_rng(SEED)
    d = []
    for _ in range(N_BOOT):
        ix = np.concatenate([by[c] for c in rng.choice(coils, len(coils))])
        d.append(sd(z.uniform.values[ix]) - sd(z.population.values[ix]))
    ci = [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))]
    prov = pd.read_csv(D.ROOT / "vars/extra/er_barriers.csv", sep=";").set_index("ID").PRO
    o["prov"] = o.coil.map(prov)
    by_prov = o.groupby("prov").agg(detector_days=("coil", "size"), population=("population", "median"),
                                    uniform=("uniform", "median")).round(3)
    out = {"k": k_final(), "days": C.CAL_DAYS, "coils": int(len(coils)), "detector_days": int(len(z)),
           "sd_log10": {"population": sd(z.population), "uniform": sd(z.uniform)},
           "median_log10_ratio": {"population": float(z.population.median()), "uniform": float(z.uniform.median())},
           "sd_uniform_minus_population": sd(z.uniform) - sd(z.population), "ci95": ci,
           "population_supported": bool(ci[0] > 0),
           "diagnostic_median_log10_ratio_by_province_all_detectors": by_prov.to_dict("index")}
    (D.RES / "score_sensitivity.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    cmd = sys.argv[1]
    {"jobs": jobs, "evaluate": evaluate}.get(cmd, lambda: {"one": one, "check": check}[cmd](*sys.argv[2:]))()
