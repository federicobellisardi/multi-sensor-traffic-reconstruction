#!/usr/bin/env python3
"""Choice of the common demand factor k from the scan of 10 February 2020 (demand_scaling.py scan).

The complete coils of 10 February 2020 are split in two halves, stratified by province (seed
20261028). k is the simulated value with the smallest median absolute log10 ratio between simulated and
observed daily volumes on the calibration half. (Matching the pooled volume is not possible: the
simulated volume saturates below the observed one because of congestion.) The other half, the other
days of 2020 and the 2021 campaign are not used for the choice.

Outputs: model/results/demand/scan_summary.csv, k_choice.json, figures/S_demand_scan.{pdf,png}
Usage (repository root): python3 model/analysis/demand_scan_eval.py
"""
import glob
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import demand_scaling as D  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import ARTICLE as A1  # noqa: E402

FIG = A1 / "figures"
OLD = str(D.ROUTING / "V6_gps_usage_classweights")  # per-pair detector rescaling (historic generator)
SEED = 20261028
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                     "pdf.fonttype": 42, "savefig.dpi": 300, "font.family": "sans-serif"})


def daily(path):
    d = pd.read_csv(path, sep=";")
    cols = [c for c in d if c.startswith("20")]
    return d.groupby("poly_lid")[cols].sum().sum(axis=1)


def split(o):
    rng = np.random.default_rng(SEED)
    calib = set()
    for _, g in o.groupby("prov"):
        coils = sorted(g.coil)
        calib |= set(rng.permutation(coils)[: (len(coils) + 1) // 2])
    return o.coil.isin(calib)


def scores(obs, sim):
    lr = np.log10(np.clip(sim, 1, None) / obs)
    return dict(n=int(len(obs)), ratio=float(sim.sum() / obs.sum()),
                spearman=float(pd.Series(sim).corr(pd.Series(obs), method="spearman")),
                median_abs_log10=float(np.median(np.abs(lr))), within_factor2=float(np.mean(np.abs(lr) < np.log10(2))))


def main():
    o = D.observations()
    o = o[o.day == "2020-02-10"].reset_index(drop=True)
    o["calib"] = split(o)
    runs = {"per-pair rescaling": OLD}
    runs.update({f"{k:.1f}": str(D.OUT / "scan" / f"k{k:.1f}") for k in D.SCAN})
    rows = []
    for name, d in runs.items():
        f = glob.glob(f"{d}/sim_200210_uniq_*.csv")
        if not f:
            continue
        sim = o.poly_lid.map(daily(f[0])).fillna(0).values
        for part, m in [("calibration", o.calib.values), ("test", ~o.calib.values), ("all", np.ones(len(o), bool))]:
            rows.append(dict(run=name, k=np.nan if name.startswith("per") else float(name), part=part,
                             **scores(o.obs.values[m], sim[m])))
    s = pd.DataFrame(rows)
    D.RES.mkdir(parents=True, exist_ok=True)
    s.to_csv(D.RES / "scan_summary.csv", index=False)
    c = s[(s.part == "calibration") & s.k.notna()].sort_values("k")
    k_star = float(c.loc[c.median_abs_log10.idxmin(), "k"])
    choice = {"k": round(k_star, 2), "criterion": "minimum median |log10(sim/obs)| on the calibration half",
              "coils_calibration": int(o.calib.sum()), "coils_test": int((~o.calib).sum()), "seed": SEED,
              "scan": sorted(c.k.tolist())}
    (D.RES / "k_choice.json").write_text(json.dumps(choice, indent=2) + "\n")

    fig, axes = plt.subplots(1, 4, figsize=(11, 2.9), constrained_layout=True)
    old = s[s.run == "per-pair rescaling"]
    for ax, col, lab in zip(axes, ["ratio", "spearman", "median_abs_log10", "within_factor2"],
                            ["Simulated / observed volume", "Spearman correlation", r"Median $|\log_{10}(\mathrm{sim}/\mathrm{obs})|$",
                             "Share within a factor of 2"]):
        for part, color, mk in [("calibration", "#1F7F8C", "o"), ("test", "#C8693F", "s")]:
            z = s[(s.part == part) & s.k.notna()].sort_values("k")
            ax.plot(z.k, z[col], marker=mk, ms=3.5, color=color, label=f"{part} coils ({int(z.n.iloc[0])})")
            r = old[old.part == part]
            if len(r):
                ax.axhline(r[col].iloc[0], color=color, ls=":", lw=0.9)
        ax.axvline(k_star, color="k", lw=0.8, ls="--")
        if col == "ratio":
            ax.axhline(1, color="#8c8c8c", lw=0.6)
        ax.set(xlabel="Demand factor $k$", ylabel=lab)
    axes[0].legend(frameon=False, fontsize=7)
    axes[0].set_title(f"$k^*$ = {k_star:.1f} (dashed); dotted: per-pair rescaling", fontsize=8, loc="left")
    for ext in ("pdf", "png"):
        fig.savefig(FIG / f"S_demand_scan.{ext}", bbox_inches="tight", dpi=300)
    print(s.round(3).to_string(index=False))
    print(json.dumps(choice, indent=1))


if __name__ == "__main__":
    main()
