#!/bin/bash
# Two simulated hours of 10 February 2020 (V6 route choice, final demand scale): checks that the
# simulator, the inputs and the Python environment work together on this machine. Writes to a
# temporary directory, not to $SIM_RUNS/demand.
set -e
. "$(dirname "$0")/config.sh"
cd "$REPO"
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
"$PY" - "$T" <<'E2'
import sys
from pathlib import Path
sys.path.insert(0, "model/analysis")
import json, demand_scaling as D
day = "2020-02-10"
k = json.load(open(D.RES / "k_choice.json"))["k"]
cfg = D.v6_config(day, D.VARIANTS["V6_scaled"], D.scaled_sources(day, {c: k for c in D.CLASSES}), None)
cfg["stop_date"] = "2020-02-10 02:00:00"
base = Path(sys.argv[1]) / "sim_smoke"
cfg["state_basename"] = str(base)
name, rc, secs = D.run(cfg, base)
assert rc == 0, f"sim_engine failed (exit {rc}); see {base}.log"
uniq = next(base.parent.glob("sim_smoke_uniq_*.csv"))
n = sum(1 for _ in open(uniq)) - 1
assert n > 1000, f"suspiciously small flux table ({n} links)"
print(f"smoke test passed: {n} links, {secs} s, engine {D.ENGINE}")
E2
