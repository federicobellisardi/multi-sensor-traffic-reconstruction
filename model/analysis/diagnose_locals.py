#!/usr/bin/env python3
"""Diagnostic: does the LOCALS source (random-origin / random-destination vehicles, 39% of the nominal
demand) contribute to the simulated link flows?

In the final V6 run of 10 February 2020 every LOCALS vehicle alive at the hourly dumps sits on one link
(poly_lid 2249, s = 0), also at 07:00, and 1.4 M of the 1.49 M created are still there at the end of the
day. If they never move, removing the source must leave the link flows unchanged.

  python3 diagnose_locals.py run        simulates 10 Feb 2020 with the same configuration as V6_scaled (k from
                                        k_choice.json) but with the LOCALS creation rate set to zero
                                        -> $SIM_RUNS/diagnostics/no_locals/   (one full day, ~20 min)
  python3 diagnose_locals.py compare    daily link flows of that run against V6_scaled, overall and on the
                                        detector links -> model/results/demand/diagnose_locals.json
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import demand_scaling as D  # noqa: E402

DAY = "2020-02-10"
NAME = "no_locals"
BASE = D.RUNS / "diagnostics" / NAME / f"sim_{D.tag(DAY)}"


def run():
    import calibrate_demand as C
    k = C.k0()
    src = D.scaled_sources(DAY, {c: k for c in D.CLASSES})
    assert "LOCALS" in src
    src["LOCALS"]["creation_rate"] = [0] * len(src["LOCALS"]["creation_rate"])
    res = D.run(D.v6_config(DAY, D.VARIANTS["V6_scaled"], src, BASE), BASE)
    print(*res, flush=True)
    sys.exit(1 if res[1] else 0)


def compare():
    import calibrate_demand as C
    f0 = next(C.basename(f"k{C.k0():.1f}", DAY).parent.glob(f"sim_{D.tag(DAY)}_uniq_*.csv"))
    f1 = next(BASE.parent.glob(f"sim_{D.tag(DAY)}_uniq_*.csv"))
    a, b = D.link_daily(f0), D.link_daily(f1)
    z = a.to_frame("with_locals").join(b.rename("no_locals"), how="outer").fillna(0.0)
    o = D.observations()
    o = o[o.day == DAY]
    zc = z.reindex(o.poly_lid.values).fillna(0.0)
    d = (z.no_locals - z.with_locals)
    dc = (zc.no_locals - zc.with_locals)
    out = {"day": DAY, "links": int(len(z)),
           "total_flow_with": float(z.with_locals.sum()), "total_flow_without": float(z.no_locals.sum()),
           "links_with_any_change": int((d != 0).sum()),
           "median_abs_rel_change_links": float(np.median(np.abs(d[z.with_locals > 0]) / z.with_locals[z.with_locals > 0])),
           "detector_links": int(len(zc)),
           "detector_total_with": float(zc.with_locals.sum()), "detector_total_without": float(zc.no_locals.sum()),
           "detector_median_abs_rel_change": float(np.median(np.abs(dc) / zc.with_locals.clip(1)))}
    (D.RES / "diagnose_locals.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    {"run": run, "compare": compare}[sys.argv[1]]()
