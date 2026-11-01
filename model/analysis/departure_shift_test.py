#!/usr/bin/env python3
"""Real runs with the departures moved earlier against the same demand without the shift (see delay_quarter.py).

  python3 departure_shift_test.py config    write the configurations into $SIM_RUNS/departure_shift/
  python3 departure_shift_test.py evaluate  -> model/results/demand/departure_shift.json
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calibrate_demand as C  # noqa: E402
import delay_quarter as Q  # noqa: E402
import demand_scaling as D  # noqa: E402

SHIFT = 3  # quarters
OUT = D.RUNS / "departure_shift"
RUNS = {"2020-02-10": ("shift", ), "2020-02-15": ("base", "shift")}
N_BOOT, SEED = 2000, 20261038


def config():
    for day, kinds in RUNS.items():
        for kind in kinds:
            d = OUT / f"{kind}_{D.tag(day)}"
            d.mkdir(parents=True, exist_ok=True)
            c = json.load(open(C.BASE / f"k{Q.K:.1f}" / f"sim_{D.tag(day)}.json"))
            c["cam_dump_dt"] = 900
            c["state_basename"] = str(d / f"sim_{D.tag(day)}")
            if kind == "shift":
                for s in c["sources"].values():
                    s["creation_rate"] = list(np.roll(np.array(s["creation_rate"]), -SHIFT).tolist())
            json.dump(c, open(d / f"sim_{D.tag(day)}.json", "w"), indent=1)
            print(d / f"sim_{D.tag(day)}.json")


def summary(obs, sim):
    lr = np.log10(np.clip(sim.sum(axis=1), 1, None) / obs.sum(axis=1))
    so, po = sim.sum(axis=0), obs.sum(axis=0)
    curve = {q: Q.err(obs, Q.shifted(sim, q)) for q in Q.SHIFTS}
    return {"pooled_hourly_error_pct": float(Q.err(obs, sim)), "median_error_pct": Q.med_err(obs, sim), "sd_log10_daily": float(lr.std()),
            "peak_am_pm": [Q.peak(po, 5, 11), Q.peak(so, 5, 11), Q.peak(po, 14, 21), Q.peak(so, 14, 21)],
            "share_21h_obs_sim": [float(po[84:88].sum() / po.sum()), float(so[84:88].sum() / so.sum())],
            "remaining_best_shift_quarters": min(curve, key=curve.get), "oracle_level_error_pct": float(Q.err(obs, Q.rescale(obs, sim)))}


def evaluate():
    out = {"shift_quarters": SHIFT, "k": Q.K}
    for day in RUNS:
        Q.DAY = day
        base_dir = Q.OUT if day == "2020-02-10" else OUT / f"base_{D.tag(day)}"
        _, obs, base = Q.load(base_dir, check=True)
        _, _, new = Q.load(OUT / f"shift_{D.tag(day)}", check=False)
        rng = np.random.default_rng(SEED)
        diff = []
        for _ in range(N_BOOT):
            i = rng.integers(0, len(obs), len(obs))
            diff.append(Q.err(obs, new, i) - Q.err(obs, base, i))
        ci = [float(x) for x in np.percentile(diff, [2.5, 97.5])]
        out[day] = {"detectors": int(len(obs)), "base": summary(obs, base), "shift": summary(obs, new),
                    "difference_pp": float(Q.err(obs, new) - Q.err(obs, base)), "difference_ci95": ci, "below_zero": bool(ci[1] < 0)}
    (D.RES / "departure_shift.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    {"config": config, "evaluate": evaluate}[sys.argv[1]]()
