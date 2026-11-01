#!/usr/bin/env python3
"""Hourly flow at held-out detectors against the raw simulation (weekday group mean, Monday run, final k).

Detectors: the test half of the February 2020 group means, never used to choose anything. Shown: detector 282 (the
example detector of the paper) and the test detectors at the quartiles of the hourly error, so that the choice of the
panels does not depend on looking good. Both directions summed. Validation only: nothing is to be selected on this.

  python3 test_detector_profile.py -> model/results/demand/test_detector_profile.{json,pdf,svg,png}
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calibrate_demand as C  # noqa: E402
import demand_scaling as D  # noqa: E402
import demand_scan_eval as E  # noqa: E402
import reconstruct_and_validate as P  # noqa: E402

DAY = "2020-02-10"
EXAMPLE = 282
OBS, SIM = "#222222", "#D55E00"


def observed(coils):
    """Hourly profile (both directions) per detector: mean of each 15-min interval over the valid weekday-group days."""
    days, _ = D.GROUPS[DAY]
    z = P.coil_table_local(2020)
    z = z[np.isin(z.index.strftime("%Y-%m-%d"), days)]
    m = z.groupby(z.index.strftime("%H:%M")).mean()
    hour = [int(x[:2]) for x in m.index]
    return {c: m[[f"{c}_0", f"{c}_1"]].sum(axis=1).groupby(hour).sum().reindex(range(24)).values for c in coils}


def simulated(lids):
    d = pd.read_csv(next((C.BASE / f"k{K:.1f}").glob(f"sim_{D.tag(DAY)}_uniq_*.csv")), sep=";")
    cols = [c for c in d if c.startswith("20")]
    g = d.groupby("poly_lid")[cols].sum()
    return {c: g.loc[l].values.astype(float) for c, l in lids.items()}


def stats(o, s):
    return {"obs_daily": float(o.sum()), "sim_daily": float(s.sum()), "ratio": float(s.sum() / o.sum()),
            "hourly_error_pct": float(100 * np.abs(s - o).sum() / o.sum()),
            "shape_correlation": float(np.corrcoef(o, s)[0, 1]),
            "peak_hour_obs": int(o.argmax()), "peak_hour_sim": int(s.argmax()),
            "best_lag_h": int(max(range(-3, 4), key=lambda l: np.nan_to_num(np.corrcoef(o, np.roll(s, -l))[0, 1])))}


K = json.load(open(D.RES / "k_choice.json"))["k"]


def main():
    g = D.group_observations()
    u = g.drop_duplicates("coil").reset_index(drop=True)
    calib = set(u.coil[E.split(u)])
    t = g[(g.day == DAY) & ~g.coil.isin(calib)]
    lids = dict(zip(t.coil, t.poly_lid))
    obs, sim = observed(lids), simulated(lids)
    st = pd.DataFrame({c: stats(obs[c], sim[c]) for c in lids}).T.sort_values("hourly_error_pct")
    picks = {f"{q}% of the detectors have a smaller error": int(st.index[int(round(q / 100 * (len(st) - 1)))]) for q in (25, 50, 75)}
    shown = ([("Detector %d (example)" % EXAMPLE, EXAMPLE)] if EXAMPLE in lids else []) + [
        (f"Detector {c} (error p{q.split('%')[0]})", c) for q, c in picks.items()]
    out = {"k": K, "day": DAY, "test_detectors": int(len(st)), "example_in_test": EXAMPLE in lids,
           "quantiles": {m: {q: float(st[m].quantile(q)) for q in (.25, .5, .75)} for m in ("hourly_error_pct", "ratio", "shape_correlation")},
           "peak_hour_within_1h": float(((st.peak_hour_obs - st.peak_hour_sim).abs() <= 1).mean()),
           "best_lag_h_counts": {int(k): int(v) for k, v in st.best_lag_h.value_counts().sort_index().items()},
           "shape_correlation_undefined": int(st.shape_correlation.isna().sum()),
           "shown": {str(c): st.loc[c].to_dict() for _, c in shown}}
    (D.RES / "test_detector_profile.json").write_text(json.dumps(out, indent=1) + "\n")
    plt.rcParams.update({"font.size": 7.5, "font.family": "sans-serif", "axes.linewidth": .6, "axes.spines.top": False,
                         "axes.spines.right": False, "pdf.fonttype": 42, "svg.fonttype": "none"})
    fig, ax = plt.subplots(1, len(shown), figsize=(7.2, 2.5), constrained_layout=True)
    for a, (title, c) in zip(ax, shown):
        a.plot(range(24), obs[c], color=OBS, lw=1.4, marker="o", ms=2.5, label="Detector")
        a.plot(range(24), sim[c], color=SIM, lw=1.3, marker="s", ms=2.5, label="Simulation")
        a.set(xlabel="Hour (start)", xticks=range(0, 24, 6), ylim=(0, None), title=f"{title}\nratio {st.ratio[c]:.2f}, error {st.hourly_error_pct[c]:.0f}%, r {st.shape_correlation[c]:.2f}")
        a.title.set_fontsize(7)
    ax[0].set_ylabel("Flow, both directions (veh/h)")
    fig.legend(*ax[0].get_legend_handles_labels(), frameon=False, loc="outside lower center", ncol=2, fontsize=7)
    for e, kw in (("pdf", {}), ("svg", {}), ("png", {"dpi": 200})):
        fig.savefig(D.RES / f"test_detector_profile.{e}", **kw)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
