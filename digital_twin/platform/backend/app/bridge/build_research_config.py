#!/usr/bin/env python3
"""Write the engine configuration of a research run. Runs in the research environment.

The configuration comes from the same functions as `demand_scaling.one`, so the science stays in
model/analysis. The platform only adds its documented overrides: demand multiplier on k, seed, window.

Usage: build_research_config.py SCIENCE_ROOT REQUEST.json OUTPUT.json
"""
import json
import sys
from pathlib import Path


def main(root, request, output):
    sys.path.insert(0, str(Path(root) / "model/analysis"))
    import demand_scaling as D

    req = json.load(open(request))
    day = req["day"]
    f = D.k_of(day) * req["demand_multiplier"]
    src = D.province_scaled(D.scaled_sources(day, {c: f for c in D.CLASSES}))
    cfg = D.v6_config(day, D.VARIANTS[req["variant"]], src, req["basename"])
    if req["seed"] is not None:
        cfg["seed"] = req["seed"]
    if req["stop_date"] is not None:
        cfg["stop_date"] = req["stop_date"]
    json.dump(cfg, open(output, "w"), indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:])
