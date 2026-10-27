#!/usr/bin/env python3
"""Prepare the 2023 assimilation environment and run the coil leave-one-out test.

1. extracts from the covid_hep git history the cartography and coil metadata used by
   the March 2023 runs (commit 0417bb8);
2. copies the raw simulation outputs of 10-17 February 2020 into a work directory;
3. runs loo_run.py for every day (3 parallel processes) and aggregates the results.

correction_2023.py with this environment reproduces the archived 10 February 2020
assimilated table to machine precision (checked during the revision).
"""
import json, subprocess, shutil, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
WORK = HERE / "work"
OUT = ROOT / "article/results/revision"
FILES = ["vars/carto/er-speed.pro", "vars/carto/er-speed.pnt", "vars/extra/er_barriers_cartodata.csv",
         "vars/extra/noturn.csv", "vars/extra/er.file_shadow", "vars/extra/correction-pivot-mapping.csv"]


def prepare():
    for f in FILES:
        dst = WORK / "ws/covid_hep" / f
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(subprocess.check_output(["git", "-C", str(ROOT), "show", f"0417bb8:{f}"]))
    (WORK / "coils").mkdir(parents=True, exist_ok=True)
    tab = WORK / "coils/coils_table_200201-000000_200331-234500.csv"
    if not tab.exists():
        shutil.copy(ROOT / "data/old_coils_data/_coils_table_200201-000000_200331-234500.csv", tab)
    # coils_ave/std files are read by the 2023 code for the min-max bands only (not used by correct())
    for f in list((ROOT / "data").glob("coils_ave_*.csv")) + list((ROOT / "data").glob("coils_std_*.csv")):
        if not (WORK / "coils" / f.name).exists():
            (WORK / "coils" / f.name).symlink_to(f)
    (WORK / "sim").mkdir(exist_ok=True)
    for f in (ROOT / "work_viasat/sim2020/uniq").glob("sim_*_*_??????_000000.csv"):
        shutil.copy(f, WORK / "sim" / f.name)


def main():
    prepare()
    for f in ["loo_run.py", "correction_2023.py"]:
        shutil.copy(HERE / f, WORK / f)
    bases = sorted(str(p).split("_uniq_")[0] for p in (WORK / "sim").glob("*_uniq_??????_000000.csv"))
    (WORK / "out").mkdir(exist_ok=True)
    from concurrent.futures import ThreadPoolExecutor
    def run(b):
        out = WORK / "out" / (Path(b).name + ".csv")
        subprocess.run([sys.executable, str(WORK / "loo_run.py"), b, str(out)], stdout=subprocess.DEVNULL, check=True)
    with ThreadPoolExecutor(3) as pool:
        list(pool.map(run, bases))
    aggregate()


def aggregate():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    d = pd.concat([pd.read_csv(f) for f in sorted((WORK / "out").glob("*.csv"))])
    d.to_csv(OUT / "loo_coils_2020.csv", index=False)
    by = d.groupby("coil")[["obs_total", "raw_abs", "loo_abs", "full_abs"]].sum()
    by["before"] = by.raw_abs / by.obs_total
    by["after"] = by.loo_abs / by.obs_total
    by["changed"] = d.groupby("coil").changed.any()
    tot = d[["raw_abs", "loo_abs", "full_abs"]].sum() / d.obs_total.sum()
    q = lambda x: {k: float(np.percentile(x, p)) for k, p in [("p25", 25), ("median", 50), ("p75", 75)]}
    summary = {
        "days": sorted(d.day.unique().tolist()), "coil_days": int(d.groupby(["coil", "day"]).ngroups),
        "coils": int(by.shape[0]), "series": int(len(d)),
        "pooled_rel_error_before": float(tot.raw_abs), "pooled_rel_error_after": float(tot.loo_abs),
        "pooled_rel_error_with_coil": float(tot.full_abs),
        "per_coil_before": q(by.before), "per_coil_after": q(by.after),
        "share_coils_changed": float(by.changed.mean()),
        "share_coils_improved": float((by.after < by.before - 1e-6).mean()),
        "share_coils_worse": float((by.after > by.before + 1e-6).mean()),
        "changed_only": {"n": int(by.changed.sum()),
                          "before_median": float(by[by.changed].before.median()),
                          "after_median": float(by[by.changed].after.median())},
    }
    (OUT / "loo_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=1))
    fig, ax = plt.subplots(figsize=(5.2, 4.8), constrained_layout=True)
    c = np.where(by.changed, "#B84A62", "#9A9A9A")
    ax.scatter(100 * by.before, 100 * by.after, c=c, s=22, edgecolor="white", lw=0.4)
    lim = [0, 100 * max(by.before.max(), by.after.max()) * 1.05]
    ax.plot(lim, lim, "k--", lw=1)
    ax.set_xlim(lim); ax.set_ylim(lim)
    ax.set_xlabel("Error on held-out coil, raw simulation (%)")
    ax.set_ylabel("Error on held-out coil, after assimilation (%)")
    ax.scatter([], [], c="#B84A62", label="reached by propagation"); ax.scatter([], [], c="#9A9A9A", label="not reached")
    ax.legend(fontsize=9, loc="upper left")
    for ext in ("png", "pdf"):
        fig.savefig(ROOT / f"article/tex/images/S_loo_coils.{ext}", dpi=300, bbox_inches="tight")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "aggregate":
        aggregate()
    else:
        main()
