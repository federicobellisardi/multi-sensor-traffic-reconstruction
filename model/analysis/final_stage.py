#!/usr/bin/env python3
"""Steps of the re-run without code 000000000 that the earlier scripts do not drive: departure shift test, runs for factors and relabelling.

  python3 final_stage.py jobs STAGE | one NAME DAY | shift | relabel
Stages: shift, before (runs without factors, every weekday), round1, round2.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calibrate_demand as C  # noqa: E402
import demand_scaling as D  # noqa: E402
import od_matrix as M  # noqa: E402
import province_demand as PD  # noqa: E402

OUT = D.RUNS / "nocode"
N_BOOT, SEED = 2000, 20261070


def job(name, day):
    if name in ("shift", "noshift"):
        return OUT / f"{name}" / f"sim_{D.tag(day)}"
    if name in D.VARIANTS:
        return D.OUT / name / f"sim_{D.tag(day)}"
    if name == "before":
        return D.RUNS / "demand_before_province/V6_scaled" / f"sim_{D.tag(day)}"
    return PD.path(int(name[5:])) / f"sim_{D.tag(day)}"


STAGES = {"final": [(n, d) for n, d in D.final_jobs()], "shift": [(n, d) for n in ("shift", "noshift") for d in C.CAL_DAYS], "before": [("before", d) for d in D.WEEK], "round1": [("round1", d) for d in C.CAL_DAYS], "round2": [("round2", d) for d in D.WEEK]}


def jobs(stage):
    for n, d in STAGES[stage]:
        b = job(n, d)
        if not list(b.parent.glob(f"{b.name}_uniq_*.csv")):
            print(n, d)


def one(name, day):
    if name in D.VARIANTS:
        res = D.one(name, day)
        print(*res, flush=True)
        sys.exit(1 if res[1] else 0)
    k = D.k_of(day)
    src = D.scaled_sources(day, {x: k for x in D.CLASSES})
    b = job(name, day)
    b.parent.mkdir(parents=True, exist_ok=True)
    if name.startswith("round"):
        f = json.load(open(PD.factors_file(int(name[5:]))))
        for s in src.values():
            ends = [f[p] for p in (PD.prov_of(s[e]) for e in ("source_location", "dest_location") if e in s) if p]
            if ends:
                g = float(np.prod(ends)) ** (1 / len(ends))
                s["creation_rate"] = [int(round(g * v)) for v in s["creation_rate"]]
    c = D.v6_config(day, D.VARIANTS["V6_scaled"], src, b)
    if name in ("shift", "noshift"):
        c["cam_dump_dt"] = 900
    if name == "noshift":
        for s in c["sources"].values():
            s["creation_rate"] = np.roll(s["creation_rate"], D.DEPARTURE_SHIFT_QUARTERS).tolist()
    res = D.run(c, b)
    print(*res, flush=True)
    sys.exit(1 if res[1] else 0)


def shift():
    import delay_quarter as Q
    out = {}
    cal = None
    for day in C.CAL_DAYS:
        Q.DAY = day
        _, obs, base = Q.load(OUT / "noshift", check=False)
        _, _, new = Q.load(OUT / "shift", check=False)
        rng = np.random.default_rng(SEED)
        dif = []
        for _ in range(N_BOOT):
            i = rng.integers(0, len(obs), len(obs))
            dif.append(Q.err(obs, new, i) - Q.err(obs, base, i))
        ci = [float(x) for x in np.percentile(dif, [2.5, 97.5])]
        out[day] = {"detectors": int(len(obs)), "without_shift": float(Q.err(obs, base)), "with_shift": float(Q.err(obs, new)), "difference_pp": float(Q.err(obs, new) - Q.err(obs, base)), "difference_ci95": ci, "below_zero": bool(ci[1] < 0)}
    (D.RES / "departure_shift.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


def relabel():
    for src in (D.RUNS / "demand_before_province/V6_scaled", PD.path(2)):
        for day in D.DAYS[2020] + D.DAYS[2021]:
            dst = src / f"sim_{D.tag(day)}"
            if day not in D.WEEK and not list(src.glob(f"sim_{D.tag(day)}_uniq_*.csv")):
                D.relabel(src / f"sim_{D.tag(D.weekday_run(day))}", dst, day)


if __name__ == "__main__":
    a = sys.argv
    {"jobs": lambda: jobs(a[2]), "one": lambda: one(a[2], a[3]), "shift": shift, "relabel": relabel}[a[1]]()
