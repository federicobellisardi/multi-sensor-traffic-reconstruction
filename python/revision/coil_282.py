#!/usr/bin/env python3
"""Coil 282 panels on Monday 10 February 2020 (Fig. 2d and Fig. 4a).

The MTS tables store UTC timestamps; they are converted to Europe/Rome before plotting
so that the observed series and the simulation share the same local clock.
Writes 1d_coil_profile.* and 4_poly_flow.* in article/tex/images and the summary used
in the supplementary coil table.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
IMG = ROOT / "article/tex/images"
DAY = pd.Timestamp("2020-02-10")
COILS = ROOT / "data/old_coils_data/_coils_table_200201-000000_200331-234500.csv"
SIM = ROOT / "work_viasat/sim2020/uniq/sim_230330113558146127_uniq_200210_000000.csv.corrected"
POLY = 214686  # polyline associated with coil 282 (poly_lid 2107)
plt.rcParams.update({"font.size": 12, "axes.spines.top": False, "axes.spines.right": False})


def save(fig, stem):
    for ext in ("png", "pdf"):
        fig.savefig(IMG / f"{stem}.{ext}", bbox_inches="tight", dpi=300)
    plt.close(fig)


coil = pd.read_csv(COILS, sep=";", usecols=["datetime", "282_0", "282_1"])
coil.index = pd.to_datetime(coil.datetime, utc=True).dt.tz_convert("Europe/Rome").dt.tz_localize(None)
day = coil.loc[(coil.index >= DAY) & (coil.index < DAY + pd.Timedelta(days=1)), ["282_0", "282_1"]]
assert len(day) == 96 and day.notna().all().all(), "incomplete coil 282 data"

fig, ax = plt.subplots(figsize=(8.2, 4.8), constrained_layout=True)
ax.plot(day.index, day["282_0"], color="#8D8D8D", lw=2, label="Direction 0")
ax.plot(day.index, day["282_1"], color="#C4C4C4", lw=2, label="Direction 1")
ax.set_xlabel("Local time, Monday 10 February 2020")
ax.set_ylabel("Vehicles / 15 min")
ax.xaxis.set_major_locator(mdates.HourLocator(byhour=range(0, 24, 3)))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
ax.set_xlim(day.index.min(), day.index.max())
ax.set_ylim(bottom=0)
ax.legend(frameon=False, ncol=1, loc="upper right")
save(fig, "1d_coil_profile")

sim = pd.read_csv(SIM, sep=";")
cols = [c for c in sim.columns if c.startswith("2020-")]
flow = sim.loc[sim.poly_cid == POLY, cols].sum()
flow.index = pd.to_datetime(flow.index)
hourly_coil = day.sum(axis=1).resample("h").sum()
fig, ax = plt.subplots(figsize=(9.0, 5.0), constrained_layout=True)
raw = pd.read_csv(str(SIM).replace(".corrected", ""), sep=";")
raw_flow = raw.loc[raw.poly_cid == POLY, cols].sum()
raw_flow.index = pd.to_datetime(raw_flow.index)
ax.plot(raw_flow.index + pd.Timedelta(minutes=30), raw_flow.values, color="#2F2F2F", marker="^", ms=5, lw=2.0,
        label="Simulation (raw)")
ax.plot(flow.index + pd.Timedelta(minutes=30), flow.values, color="#8D8D8D", marker="o", ms=5, lw=2.4,
        label="Simulation (assimilated)")
ax.plot(hourly_coil.index + pd.Timedelta(minutes=30), hourly_coil.values, color="#B0B0B0", marker="s", ms=5,
        lw=2.2, ls="--", label="Coil 282")
ax.set_xlabel("Local time")
ax.set_ylabel(r"$\Phi$ (veh/h)")
ax.xaxis.set_major_locator(mdates.HourLocator(interval=3))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
ax.legend(loc="upper left", frameon=False)
save(fig, "4_poly_flow")

hour = day.resample("h").sum()
summary = {d: {"samples": int(day[d].notna().sum()), "daily_sum": int(day[d].sum()),
               "peak_hourly": int(hour[d].max()), "peak_hour": hour[d].idxmax().strftime("%H:%M")}
           for d in ["282_0", "282_1"]}
out = ROOT / "article/results/revision"
out.mkdir(parents=True, exist_ok=True)
(out / "coil_282_summary.json").write_text(json.dumps(summary, indent=2))
print(summary)

corr = {"raw_vs_coil_pearson": float(raw_flow.reset_index(drop=True).corr(hourly_coil.reset_index(drop=True))),
        "raw_daily": float(raw_flow.sum()), "assimilated_daily": float(flow.sum()), "coil_daily": float(hourly_coil.sum())}
summary["comparison"] = corr
(out / "coil_282_summary.json").write_text(json.dumps(summary, indent=2))
print(corr)
