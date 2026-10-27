#!/usr/bin/env python3
"""Sensitivity of the 2020 validation to the clock of the MTS coil table.

The coil table stores UTC timestamps, while the assimilation code drops the time zone
and compares them with simulation hours in local time. Here the 2020 assimilation is
rerun with the coil timestamps converted to Europe/Rome and the Viasat profile error is
recomputed. Requires the work directory prepared by run_loo.py.
"""
import contextlib, io, json, os, sys, shutil
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
WORK = HERE / "work"
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(WORK))
os.environ["WORKSPACE"] = str(WORK / "ws")
from correction_2023 import SimPostCorrection  # noqa: E402
import validation_all_links as V  # noqa: E402

local_dir = WORK / "coils_local"
local_dir.mkdir(exist_ok=True)
src = WORK / "coils/coils_table_200201-000000_200331-234500.csv"
t = pd.read_csv(src, sep=";")
t["datetime"] = (pd.to_datetime(t.datetime, utc=True).dt.tz_convert("Europe/Rome")
                 .dt.tz_localize(None).dt.strftime("%Y-%m-%d %H:%M:%S+00:00"))
t.to_csv(local_dir / src.name, sep=";", index=False)
for f in (WORK / "coils").glob("coils_[as]*_*.csv"):
    if not (local_dir / f.name).exists():
        (local_dir / f.name).symlink_to(f.resolve())

sim_dir = WORK / "sim_local"
sim_dir.mkdir(exist_ok=True)
for f in (WORK / "sim").glob("*_??????_000000.csv"):
    shutil.copy(f, sim_dir / f.name)
for f in (ROOT / "work_viasat/sim2020/uniq").glob("*.json"):
    shutil.copy(f, sim_dir / f.name)
for f in sorted(sim_dir.glob("*_uniq_??????_000000.csv")):
    with contextlib.redirect_stdout(io.StringIO()):
        SimPostCorrection({"coils_table_dir": str(local_dir)}, str(f).split("_uniq_")[0]).correct([])

gps, days, _ = V.load_viasat(V.YEARS[2020]["viasat"])
res = {}
for label, d in [("archived", V.YEARS[2020]["sim"]), ("coils_local_time", sim_dir)]:
    m, *_ = V.link_metrics(V.load_sim(V.sim_files(d, [])), gps, len(days))
    res[label] = V.q(m.mae_pp)
(ROOT / "article/results/revision/tz_sensitivity_2020.json").write_text(json.dumps(res, indent=2))
print(json.dumps(res, indent=1))
