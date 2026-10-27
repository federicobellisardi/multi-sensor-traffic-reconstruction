# 1. Research inventory (Phase 1 audit, 2026-10-27)

Repository root: `covid_hep/` (remote `physycom/covid_hep`, private). Manuscript repo: `article/`
(remote `federicobellisardi/multi-sensor-traffic-reconstruction`, private, branch `revision-v2`).

## 1.1 Manuscripts and formatting reference

| Item | Location | Notes |
|---|---|---|
| Original manuscript (historical) | `paper/main.tex` | Springer `svjour3`-era draft; figures in `paper/*.png` |
| Revised main manuscript (**formatting reference**) | `article/tex/epjds_main_draft.tex` | `sn-jnl` class, `[pdflatex,Numbered]`, natbib numbers + `unsrtnat`, A4, 1.8 cm margins, `\doublespacing`, `figure*` composites, bold-lead captions "\textbf{Title.} \textbf{(a)} …" |
| Revised supplement | `article/tex/epjds_supplementary_draft.tex` | `article` class 11pt, A4 1.8 cm, S-numbered sections/figures/tables, `xr-hyper` to main |
| Bibliography | `article/tex/references.bib` | ~70 entries; partially verified in revision-v2 |
| Revision report | `article/REVISION_REPORT.md` | 21-point revision, lists remaining TODOs and code defects |

## 1.2 Data (available)

| Dataset | Path | Period | Licence / status |
|---|---|---|---|
| TIM mobile-phone OD (raw, ACE-level tables) | `data/tables_rpc-rpc/` (14 GB) | Jan 2020 | **Proprietary**, never commit |
| OD averages (weekday/weekend, municipality & province) | `data/od-*.csv`, `MCF/data/raw_inputs/od-average-*.csv` | Jan 2020 | Derived from proprietary; not redistributable |
| MTS coil 15-min counts (UTC) | `data/coils_table_2[234]*.csv` | 2022-01-01 → 2024-03-31 | Public (Regione E-R, flussi-online) |
| MTS coil averages/std by weekday×season | `data/coils_ave_*`, `data/coils_std_*` | 2022–2024 | Public-derived |
| MTS coil counts Feb–Mar 2020 | `data/old_coils_data/_coils_table_200201…` | 2020 | Public |
| Coil registry | `data/Anagrafica_20220615.csv` | 2022 | Public (province, road owner, road number, lanes) |
| Viasat GPS link counts | `work_viasat/viasat_2020…`, `…2021…` | 10–17 Feb 2020; 28 Jun–4 Jul 2021 | **Proprietary** |
| Archived simulations (raw + assimilated) | `work_viasat/sim2020/uniq`, `sim2021/uniq` | same weeks | Derived; minimocas outputs |
| 2023 exposure runs (webserver output) | `work_iconsultin/data2/{feriali,festivi}` | 12 weekdays (one/month) + 11 Sundays, 2023 | Derived |
| ISTAT–ACI regional accident kit, Emilia-Romagna | `work_incidenti/data/202[234].xlsx` | 2022–2024 | Public (ISTAT). Tables by hour, weekday, month, province, road category, urban/extra-urban, weekday×night band×province |
| ACI–ISTAT accidents per named road segment | `data/incidenti.csv` | 2003–2017, Italy (139 rows in E-R) | Public (ACI "localizzazione"), road-level counts with segment length |
| Road graph | `vars/carto/er-speed.{pro,pnt}`, `article/data/uniq/carto.geojson` | OSM-derived | 4,186 polylines, 2,704 nodes; **no OSM highway class or ref attribute** |

## 1.3 Code

| Component | Path | Status |
|---|---|---|
| minimocas C++ simulator | `minimocas/` (submodule, private, **no licence file**), binary `bin/sim_engine`, `bin/pysim*.so` | Builds locally (cmake, boost present). RNG seed hard-coded to 1 (`simulation.cpp:746`) → deterministic |
| Config generation from OD | `python/config.py`, `dashboard/fastapi/python/conf.py`, revision copy `article/python/revision/rerun/conf_2023.py` | Known defect: 23/24 hourly values read; hour mapping offset |
| Coil assimilation | `dashboard/fastapi/python/correction.py` (webserver, depth 5), archived `article/python/revision/loo/correction_2023.py` (depth 3; reproduces archived tables to machine precision) | Known defects: UTC clock of coil table; sibling turning weights compounded |
| Validation | `article/python/revision/validation_all_links.py` | All-link MAE, baselines, Ward clustering |
| LOO assimilation test | `article/python/revision/loo/` | 149 coils, 610 coil-days |
| Accident exposure | `article/python/revision/incident_risk.py` | R(h), α fit, hazard maps |
| Webserver | `dashboard/` (FastAPI `sim-ws.py` 374 LOC; Django GUI with `dashboard`, `mtsdata`, `simapi` apps; `crono` cron fetcher of MTS API; nginx; 4 docker-compose variants) | Dockerfile clones private repos with an SSH deploy key → not buildable by third parties |
| Exploratory | `work_*` (≈30 dirs), `MCF/` (alternative "conserved field" framing), `python/scan`, `python/od-fit` | Provenance only |

## 1.4 Existing experiments and reproducibility

| Result (revision-v2) | Reproducible here? | Notes |
|---|---|---|
| All-link Viasat profile MAE (848/845 links) | Yes (script + archived sims + proprietary Viasat present locally) | |
| Baselines (OD profile, MTS mean profile) | Yes | MTS profile beats reconstruction |
| LOO on 149 coils | Yes | |
| UTC-clock sensitivity | Yes | |
| Coil-282 example | Yes | |
| Accident R(h), α = 0.72 [0.58, 0.88] | Yes | uses 2023 webserver runs; exposure ≠ accident days composition |
| Hazard-weighted maps H_i, S_i, C_i, D_i | Yes but scientifically weak | regional R(h) × link profile, no spatial accident info |
| Re-simulation from configs | In progress (`rerun/work/repro/20200210`) | tests bit-reproducibility of archived run |
| Corrected-clock configs | Generated (`rerun/work/conf_fixed`), not yet simulated | |
| Webserver end-to-end deployment | **No** | private repos, SSH key, config.json.docker not in repo |

## 1.5 Scientific limitations identified

1. Temporal mismatch: demand Jan 2020; validation Feb 2020 & Jun 2021; accidents 2022–2024; exposure runs 2023 driven by Jan 2020 OD.
2. Penetration η_i is computed from the simulation itself ⇒ Viasat validates **shape only**; absolute volumes are validated only at coils (LOO: 59.8 % → 56.7 % pooled abs. error).
3. Simulated profile leads observations by ≈1 h; 23:00–24:00 has no demand.
4. Simulator has no dynamic assignment; fixed seed means no stochastic uncertainty estimate.
5. Accident data have no locations at sub-provincial resolution (2022–2024); the hazard maps are a re-weighting of simulated traffic, not risk.
6. Coil table timestamps in UTC not converted in assimilation.
7. Road category is not an attribute of the graph (needs OSM join).

## 1.6 Candidate contributions

* **Paper 1** – quantitative, network-wide reconstruction assessment with explicit separation of shape vs volume validation, baselines, LOO, coverage/parameter/demand/seed sensitivity, and a corrected-clock rerun.
* **Paper 2** – exposure-normalised temporal accident risk for 2022–2024 using *observed* coil exposure from the same years (public), simulated exposure, and static exposure; count models (Poisson/NB) for the volume–accident exponent; propagation of exposure uncertainty; spatial analysis limited to provinces / road categories / named roads where public data exist.
* **Paper 3** – software/operational paper; contingent on licensing and public release of minimocas and the platform (currently blocked).
