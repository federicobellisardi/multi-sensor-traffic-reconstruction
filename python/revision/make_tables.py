#!/usr/bin/env python3
"""Write the LaTeX tables of the revised manuscript from article/results/revision/."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp

ROOT = Path(__file__).resolve().parents[3]
RES = ROOT / "article/results/revision"
TAB = ROOT / "article/tex/tables"
TAB.mkdir(exist_ok=True)
S = json.loads((RES / "validation_summary.json").read_text())


def f(x, d=2):
    return f"{x:.{d}f}"


def pct(x):
    return f"{100 * x:.0f}"


def validation_table():
    rows = []
    for y in ["2020", "2021"]:
        d = S[y]
        m, e = d["mae_pp"], d["eps_rel"]
        rows.append(rf"{y} & all & {d['usable_links']} & {f(m['median'])} & {f(m['p25'])}--{f(m['p75'])} & "
                    rf"{f(m['p10'])}--{f(m['p90'])} & {pct(e['median'])} & {f(d['pearson']['median'])} \\")
        for k in ["-1", "-2", "-3", "-4"]:
            c = d["by_class"].get(k)
            if not c:
                continue
            mm, ee = c["mae_pp"], c["eps_rel"]
            iqr = f"{f(mm['p25'])}--{f(mm['p75'])}" if c["n"] >= 10 else "--"
            span = f"{f(mm['p10'])}--{f(mm['p90'])}" if c["n"] >= 10 else "--"
            rows.append(rf" & $10^{{{k}}}$ & {c['n']} & {f(mm['median'])} & {iqr} & {span} & {pct(ee['median'])} & {f(c['pearson_median'])} \\")
        if y == "2020":
            rows.append(r"\midrule")
    body = "\n".join(rows)
    (TAB / "validation_all_links.tex").write_text(rf"""\begin{{table}}[htbp]
\centering
\caption{{Profile error of the assimilated simulation against penetration-normalized Viasat profiles on all usable matched links, by campaign and penetration class $\eta$. MAE in percentage points (Eq.~\eqref{{eq:profile_error}}); $\varepsilon$ is the median relative error (Eq.~\eqref{{eq:relative_error}}); $r$ is the median Pearson correlation of the hourly shares. Classes with fewer than ten links (three links with $\eta\sim10^{{-5}}$ in 2020, two in 2021) are included in the totals only.}}
\label{{tab:validation_all}}
\begin{{tabular}}{{@{{}}llrrrrrr@{{}}}}
\toprule
Campaign & Class & Links & Median MAE & IQR & 10th--90th pct. & $\varepsilon$ [\%] & $r$ \\
\midrule
{body}
\bottomrule
\end{{tabular}}
\end{{table}}
""")


def baseline_table():
    rows = []
    for y in ["2020", "2021"]:
        d = S[y]
        for lab, key in [("Simulation (assimilated)", "mae_pp"), ("Simulation (raw)", "mae_pp_raw"),
                         ("Simulation shifted by $+1$~h", "mae_pp_shift1"),
                         ("OD demand profile", "mae_pp_od"), ("MTS mean profile", "mae_pp_mts")]:
            m = d[key]
            extra = ""
            if key == "mae_pp_od":
                extra = pct(d["share_sim_better_than_od"])
            elif key == "mae_pp_mts":
                extra = pct(d["share_sim_better_than_mts"])
            else:
                extra = "--"
            rows.append(rf"{y if lab.startswith('Simulation (a') else ''} & {lab} & {f(m['median'])} & {f(m['p25'])}--{f(m['p75'])} & {extra} \\")
        if y == "2020":
            rows.append(r"\midrule")
    (TAB / "baselines.tex").write_text(r"""\begin{table}[htbp]
\centering
\caption{Median and interquartile range of the link MAE (pp) for the reconstruction and for two profiles applied identically to every link: the hourly profile of the injected OD demand and the mean normalized profile of the MTS coils (2020: the """ + str(S["2020"]["mts_coils"]) + r""" coil directions with complete data on all eight validation days; 2021: summer weekday averages of """ + str(S["2021"]["mts_coils"]) + r""" coil directions from the 2022 MTS archive). The last column gives the percentage of links on which the assimilated simulation has a lower MAE than the baseline.}
\label{tab:baselines}
\begin{tabular}{@{}llrrr@{}}
\toprule
Campaign & Profile & Median MAE & IQR & Simulation better [\%] \\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\end{tabular}
\end{table}
""")


def penetration_tables():
    m20 = pd.read_csv(RES / "link_metrics_2020.csv")
    m21 = pd.read_csv(RES / "link_metrics_2021.csv")
    ks = ks_2samp(m20.log_eta, m21.log_eta)
    rows = []
    for y, m in [("2020", m20), ("2021", m21)]:
        rows.append(rf"{y} & {len(m)} & {f(np.median(m.log_eta), 3)} & {f(100 * m.eta.median(), 3)} & {f(100 * m.eta.mean(), 3)} \\")
    (TAB / "penetration_summary.tex").write_text(r"""\begin{table}[htbp]
\centering
\caption{Link penetration $\eta_i$ (Viasat probes over simulated vehicles on the same days). Two-sample Kolmogorov--Smirnov test between the campaigns: $D=""" + f(ks.statistic, 3) + r"""$, $p=""" + (f"{ks.pvalue:.1e}".replace("e-0", r"\times10^{-").replace("e-", r"\times10^{-") + "}") + r"""$.}
\label{tab:penetration-summary}
\begin{tabular}{@{}lrrrr@{}}
\toprule
Campaign & Links & Median $\log_{10}\eta$ & Median $\eta$ [\%] & Mean $\eta$ [\%] \\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\end{tabular}
\end{table}
""")
    S["ks"] = {"D": float(ks.statistic), "p": float(ks.pvalue)}


def representatives_table():
    c = S["clustering_2020"]
    rows = [rf"{r['cluster'] + 1} & {r['cid']} & {f(r['mae_pp'])} & {pct(r['eps_rel'])} & {f(r['mae_pp_rank_pct'], 0)} \\"
            for r in sorted(c["representatives"], key=lambda r: r["cluster"])]
    (TAB / "representatives.tex").write_text(r"""\begin{table}[htbp]
\centering
\caption{Representative polylines of Fig.~9 in the main text. The last column is the percentage of the """ + str(S["2020"]["usable_links"]) + r""" usable 2020 links with a lower MAE. Minimum pairwise separation: """ + f(c["min_separation_km"], 1) + r"""~km.}
\label{tab:representatives}
\begin{tabular}{@{}rrrrr@{}}
\toprule
Subcluster & Polyline & MAE [pp] & $\varepsilon$ [\%] & Links with lower MAE [\%] \\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\end{tabular}
\end{table}
""")


def loo_table():
    p = RES / "loo_summary.json"
    if not p.exists():
        return
    L = json.loads(p.read_text())
    (TAB / "loo.tex").write_text(r"""\begin{table}[htbp]
\centering
\caption{Leave-one-out test of the coil assimilation, 10--17 February 2020. For each coil with complete data on a given day, the coil is removed from the assimilation and from the set of polylines that stop the propagation; the error is $\sum_h|u(h)-c(h)|/\sum_h c(h)$ on the held-out coil link, summed over directions and days.}
\label{tab:loo}
\begin{tabular}{@{}lrr@{}}
\toprule
 & Raw simulation & After assimilation \\
\midrule
Pooled relative error [\%] & """ + f(100 * L["pooled_rel_error_before"], 1) + " & " + f(100 * L["pooled_rel_error_after"], 1) + r""" \\
Median over coils [\%] & """ + f(100 * L["per_coil_before"]["median"], 1) + " & " + f(100 * L["per_coil_after"]["median"], 1) + r""" \\
Interquartile range [\%] & """ + f"{f(100 * L['per_coil_before']['p25'], 1)}--{f(100 * L['per_coil_before']['p75'], 1)}" + " & " + f"{f(100 * L['per_coil_after']['p25'], 1)}--{f(100 * L['per_coil_after']['p75'], 1)}" + r""" \\
\midrule
Coils tested & \multicolumn{2}{r}{""" + str(L["coils"]) + r"""} \\
Coil-days & \multicolumn{2}{r}{""" + str(L["coil_days"]) + r"""} \\
Coils reached by the propagation [\%] & \multicolumn{2}{r}{""" + pct(L["share_coils_changed"]) + r"""} \\
Coils improved / worsened [\%] & \multicolumn{2}{r}{""" + pct(L["share_coils_improved"]) + " / " + pct(L["share_coils_worse"]) + r"""} \\
\bottomrule
\end{tabular}
\end{table}
""")


if __name__ == "__main__":
    validation_table()
    baseline_table()
    penetration_tables()
    representatives_table()
    loo_table()
    (RES / "validation_summary.json").write_text(json.dumps(S, indent=2))
    print(sorted(p.name for p in TAB.glob("*.tex")), S["ks"])
