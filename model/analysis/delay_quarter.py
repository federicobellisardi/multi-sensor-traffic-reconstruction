#!/usr/bin/env python3
"""Delay of the simulated flow at 15-min resolution and how much of the hourly error it explains.

Calibration detectors only, weekday group mean against the Monday run at the final k, both directions summed. The run has
cam_dump_dt = 900 and is otherwise the calibration run. The simulated flow is shifted offline, circularly, and the error is
computed on hourly bins. Decomposition of the error: baseline, best global shift, oracle level per detector (simulated daily
volume rescaled to the observed one, not a usable model, only an upper bound), both. Bootstrap over detectors.

  python3 delay_quarter.py config    write the configuration of the run into $SIM_RUNS/delay_quarter/
  python3 delay_quarter.py evaluate  -> model/results/demand/delay_quarter.json
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

DAY = "2020-02-10"
K = json.load(open(D.RES / "k_choice.json"))["k"]
OUT = D.RUNS / "delay_quarter"
UNIQ_HOURLY = [None]  # hourly uniq of the calibration run, the quantity used for the calibration
SHIFTS = range(-4, 9)  # quarters; positive = simulated flow moved earlier
N_BOOT, SEED = 2000, 20261037


def config():
    OUT.mkdir(parents=True, exist_ok=True)
    c = json.load(open(C.BASE / f"k{K:.1f}" / f"sim_{D.tag(DAY)}.json"))
    c["cam_dump_dt"] = 900
    c["state_basename"] = str(OUT / f"sim_{D.tag(DAY)}")
    json.dump(c, open(OUT / f"sim_{D.tag(DAY)}.json", "w"), indent=1)


def load(out=None, check=True, test=False):
    out = out or OUT
    g = D.group_observations()
    u = g.drop_duplicates("coil").reset_index(drop=True)
    calib = set(u.coil[E.split(u)])
    t = g[(g.day == DAY) & (~g.coil.isin(calib) if test else g.coil.isin(calib))]
    days, _ = D.GROUPS[DAY]
    z = P.coil_table_local(2020)
    z = z[np.isin(z.index.strftime("%Y-%m-%d"), days)]
    m = z.groupby(z.index.strftime("%H:%M")).mean()
    obs = np.array([m[[f"{c}_0", f"{c}_1"]].sum(axis=1).values for c in t.coil])
    # barriers, not uniq: uniq counts distinct vehicles per interval, so it is not additive across 15-min intervals
    b = pd.read_csv(next(out.glob(f"sim_{D.tag(DAY)}_barriers_*.csv")), sep=";")
    cc = [[f"{c}_IN", f"{c}_OUT"] for c in t.coil]
    q = np.array([b[x].sum(axis=1).values for x in cc], dtype=float)
    # rows are labelled at the end of the interval; row 00:00 is zero and the engine does not write the last interval
    assert q.shape[1] == 95 and b.datetime.iloc[-1].endswith("23:30:00") and q[:, 0].sum() == 0
    sim = np.column_stack([q[:, 1:], q[:, -1], q[:, -1]])  # 23:30 and 23:45 taken equal to 23:15
    if check:
        h = pd.read_csv(next((C.BASE / f"k{K:.1f}").glob(f"sim_{D.tag(DAY)}_barriers_*.csv")), sep=";")
        ref = np.array([h[x].sum(axis=1).values for x in cc], dtype=float)[:, 1:23]
        assert np.array_equal(hourly(sim)[:, :22], ref), "quarters do not sum to the hourly run"
        u = pd.read_csv(next((C.BASE / f"k{K:.1f}").glob(f"sim_{D.tag(DAY)}_uniq_*.csv")), sep=";")
        uc = [c for c in u if c.startswith("20")]
        UNIQ_HOURLY[:] = [u.groupby("poly_lid")[uc].sum().loc[t.poly_lid.values].values.astype(float)]
    return t.coil.values, obs, sim


def hourly(x):
    return x.reshape(x.shape[0], 24, 4).sum(axis=2)


def shifted(sim, q):
    return np.roll(sim, -q, axis=1)


def err(obs, sim, rows=None):
    rows = np.arange(len(obs)) if rows is None else rows
    o, s = hourly(obs[rows]), hourly(sim[rows])
    return 100 * np.abs(s - o).sum() / o.sum()


def med_err(obs, sim):
    o, s = hourly(obs), hourly(sim)
    return float(np.median(100 * np.abs(s - o).sum(axis=1) / o.sum(axis=1)))


def rescale(obs, sim):
    return sim * (obs.sum(axis=1, keepdims=True) / np.clip(sim.sum(axis=1, keepdims=True), 1, None))


def peak(p, a, b):
    i = np.arange(a * 4, b * 4)
    return float(i[p[i].argmax()] / 4)


def departures():
    """Injected agents per hour of the run (all sources, constant within the hour), per quarter."""
    c = json.load(open(OUT / f"sim_{D.tag(DAY)}.json"))
    r = np.array([v["creation_rate"] for v in c["sources"].values()], dtype=float).sum(axis=0)
    assert len(r) == 96, len(r)
    return r


def best_corr_lag(x, y):
    """Quarters by which y must move earlier to correlate best with x."""
    return max(SHIFTS, key=lambda q: np.corrcoef(x, np.roll(y, -q))[0, 1])


def evaluate():
    coil, obs, sim = load()
    lr = np.log10(np.clip(sim.sum(axis=1), 1, None) / obs.sum(axis=1))
    curve = {q: float(err(obs, shifted(sim, q))) for q in SHIFTS}
    q0 = min(curve, key=curve.get)
    rng = np.random.default_rng(SEED)
    bq, gain = [], []
    for _ in range(N_BOOT):
        i = rng.integers(0, len(obs), len(obs))
        e = {q: err(obs, shifted(sim, q), i) for q in SHIFTS}
        b = min(e, key=e.get)
        bq.append(b)
        gain.append(e[0] - e[b])
    per = [min(SHIFTS, key=lambda q: 100 * np.abs(hourly(shifted(sim[[i]], q)) - hourly(obs[[i]])).sum()) for i in range(len(obs))]
    so, po = sim.sum(axis=0), obs.sum(axis=0)
    dep = departures()
    ou = hourly(obs)
    out = {"k": K, "day": DAY, "volume_source": "barriers (15-min)",
           "baseline_pooled_error_hourly_uniq_pct": float(100 * np.abs(UNIQ_HOURLY[0] - ou).sum() / ou.sum()),
           "barriers_over_uniq_daily": float(sim.sum() / UNIQ_HOURLY[0].sum()), "detectors": int(len(obs)), "shift_unit": "quarters; positive = simulated flow earlier",
           "pooled_hourly_error_pct_by_shift": curve, "best_shift_quarters": q0, "best_shift_hours": q0 / 4,
           "best_shift_bootstrap95_quarters": [float(x) for x in np.percentile(bq, [2.5, 97.5])],
           "error_gain_at_best_pp_bootstrap95": [float(x) for x in np.percentile(gain, [2.5, 97.5])],
           "per_detector_best_shift_quartiles": [float(x) for x in np.percentile(per, [25, 50, 75])],
           "decomposition_pooled_pct": {"baseline": float(err(obs, sim)), "best_shift": float(err(obs, shifted(sim, q0))),
                                        "oracle_level": float(err(obs, rescale(obs, sim))),
                                        "oracle_level_and_best_shift": float(err(obs, rescale(obs, shifted(sim, q0))))},
           "decomposition_median_per_detector_pct": {"baseline": med_err(obs, sim), "best_shift": med_err(obs, shifted(sim, q0)),
                                                     "oracle_level": med_err(obs, rescale(obs, sim)),
                                                     "oracle_level_and_best_shift": med_err(obs, rescale(obs, shifted(sim, q0)))},
           "daily_sd_log10_any_shift": float(lr.std()), "daily_within_factor2": float(np.mean(np.abs(lr) < np.log10(2))),
           "aggregate_peak_hours": {"obs_am": peak(po, 5, 11), "sim_am": peak(so, 5, 11), "departures_am": peak(dep, 5, 11),
                                    "obs_pm": peak(po, 14, 21), "sim_pm": peak(so, 14, 21), "departures_pm": peak(dep, 14, 21)},
           "aggregate_lag_quarters": {"sim_vs_obs": best_corr_lag(po, so), "departures_vs_obs": best_corr_lag(po, dep),
                                      "sim_vs_departures": best_corr_lag(dep, so)},
           "aggregate_share_21h": {"obs": float(po[84:88].sum() / po.sum()), "sim": float(so[84:88].sum() / so.sum())}}
    (D.RES / "delay_quarter.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    {"config": config, "evaluate": evaluate}[sys.argv[1]]()
