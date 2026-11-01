#!/usr/bin/env python3
"""Level of the demand for each N, then choice of N: destination code 000000000 dropped, relation radius 20 km.

Rule fixed before the runs (31 Oct), calibration half only. For each N in 100, 150, 200, the multiplier m of k in 1.0, 1.15,
1.3 is chosen per day type (Monday, Saturday) by the minimum of the unweighted mean squared log10(sim/obs), the criterion of
k_choice.json; a choice at the edge of the grid is reported. N are then compared at their own m, group means of Monday and
Saturday together: the reference is the N with the lowest sd of log10(sim/obs), and the smallest N whose paired bootstrap
interval over detectors of the sd difference from the reference has a lower end not above zero is selected. The selected N
goes to the 2021 detectors only if it beats the frozen model by the rule in od_matrix.py; otherwise the model stays frozen
and 2021 is not read. The ranking stays that of od_matrix.py (with the code): 99 of the top 100 are the same without it.

  python3 od_matrix_k.py jobs | one N M DAY | evaluate -> model/results/demand/od_matrix_k.json
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calibrate_demand as C  # noqa: E402
import demand_scaling as D  # noqa: E402
import od_matrix as M  # noqa: E402
import source_value as V  # noqa: E402

NS, MS = (100, 150, 200), (1.0, 1.15, 1.3)
SEED = 20261045


def name(n):
    return f"N{n}_r20_x"


def base(n, m, day):
    return M.base(name(n), day) if m == 1.0 else M.OUT / f"{name(n)}_m{m}" / f"sim_{D.tag(day)}"


def jobs():
    for n in NS:
        for m in MS:
            for day in C.CAL_DAYS:
                if not list(base(n, m, day).parent.glob(f"sim_{D.tag(day)}_uniq_*.csv")):
                    print(n, m, day)


def one(n, m, day):
    n, m = int(n), float(m)
    c, _ = M.config(name(n), day, m, base(n, m, day))
    res = D.run(c, base(n, m, day))
    print(*res, flush=True)
    sys.exit(1 if res[1] else 0)


def evaluate():
    t = M.table("cal")
    frozen = M.daily(M.frozen_path, t)
    rng = np.random.default_rng(SEED)
    out, sims = {}, {}
    for n in NS:
        chosen, curve = {}, {}
        for day in C.CAL_DAYS:
            q = t[t.day == day]
            loss = {m: float(np.mean(np.log10(np.clip(V.daily(base(n, m, day).parent, day, q.poly_lid), 1, None) / q.obs.values) ** 2)) for m in MS}
            chosen[day] = min(loss, key=loss.get)
            curve[day] = loss
        sims[n] = M.daily(lambda d: base(n, chosen[d], d).parent, t)
        c = M.compare(t, sims[n], frozen, rng)
        c["beats_frozen"] = bool(c["sd_diff_ci95"][1] < 0 or (c["spearman_diff_ci95"][0] > 0 and c["new"]["sd_log10"] <= c["frozen"]["sd_log10"]))
        out[n] = {"m": chosen, "mean_sq_log10": curve, "edge": {d: chosen[d] in (MS[0], MS[-1]) for d in chosen}, "against_frozen": c}
    ref = min(NS, key=lambda n: out[n]["against_frozen"]["new"]["sd_log10"])
    for n in NS:
        out[n]["sd_diff_from_reference_ci95"] = None if n == ref else M.compare(t, sims[n], sims[ref], rng)["sd_diff_ci95"]
    sel = min(n for n in NS if n == ref or out[n]["sd_diff_from_reference_ci95"][0] <= 0)
    res = {"by_N": out, "reference": ref, "selected": sel, "goes_to_2021": out[sel]["against_frozen"]["beats_frozen"]}
    (D.RES / "od_matrix_k.json").write_text(json.dumps(res, indent=1) + "\n")
    for n in NS:
        c = out[n]["against_frozen"]
        print(n, out[n]["m"], "edge", out[n]["edge"], {k: round(v, 3) for k, v in c["new"].items()}, "sd", [round(x, 4) for x in c["sd_diff_ci95"]], "sp", [round(x, 3) for x in c["spearman_diff_ci95"]], c["beats_frozen"], "ref", out[n]["sd_diff_from_reference_ci95"])
    print("frozen", {k: round(v, 3) for k, v in c["frozen"].items()}, "reference", ref, "selected", sel, "goes to 2021", res["goes_to_2021"])


if __name__ == "__main__":
    {"jobs": jobs, "evaluate": evaluate}.get(sys.argv[1], lambda: one(*sys.argv[2:]))()
