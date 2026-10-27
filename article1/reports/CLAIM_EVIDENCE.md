# Claim-to-evidence audit

Date: 2026-10-27. Status labels concern the present local package, not journal
acceptance or independent third-party reproduction.

| Claim / item | Evidence | Status and limit |
|---|---|---|
| 848/845 usable links; MAE 1.34/1.49 pp | `analysis/validate_archive.py`; `results/validation_summary.json`; Fig. 5 | Recomputed from original local GPS and archive; agrees with old metrics to 1e-9. Shape only; restricted geography. |
| Raw MAE 1.33/1.39 pp | Same pipeline and archived uncorrected tables | Recomputed; assimilation does not improve median GPS shape error. |
| OD 1.40/1.52 pp; MTS 1.15/1.22 pp | Same pipeline; main Table 1 | Recomputed. 2021 MTS uses 2022 averages and revised missingness handling. |
| Weekend MAE 1.96/2.18 pp | `results/daytype_summary.csv`; Fig. 5c,d | New descriptive calculation. Two days, different support and probe totals; no causal weekend explanation. |
| Probe-count strata | `tables/probe_strata.tex`; validation JSON | New descriptive calculation independent of simulated denominator. Spatial/fleet dependence persists. |
| Pooled LOO 59.8% to 56.7% | Existing `article/results/revision/loo_coils_2020.csv`; new aggregate and Fig. 6c | Reaggregated, not independently rerun. UTC bias and 18 missing directional records make this provisional. |
| Bootstrap gain 0.39–7.02 pp | `results/loo_uncertainty.json` | New conditional coil-resampling interval, 5,000 replicates. Does not cover spatial correlation or implementation bias. |
| One-hour pooled simulated lead | `results/aggregate_profiles_*.csv`; Fig. 6a,b | Recomputed diagnostic; pooling differs in road weights by data source. No physical clock cause established. |
| Shifted-profile 1.29/1.34 pp | Existing `article/results/revision/link_metrics_*.csv`, column `mae_pp_shift1` | Inherited sensitivity, not a corrected simulation or primary validation. |
| Coil 282 counts/correlation | Existing `article/results/revision/coil_282_summary.json`; inherited Fig. 3 | Inherited illustrative result; not recomputed by new pipeline. Not held-out. |
| Regional demand and maps | Source manuscript figures and OD/network pipelines | Inherited figures 1–4; complete regeneration and map-attribution review outstanding. |
| Held-out terminal direction can disappear | New sensor pilot; polyline 260156; `IMPLEMENTATION_AUDIT.md` | Directly observed. Pilot restricts sample rather than silently dropping test records. Full code repair pending. |
| Historic simulation replay | `analysis/replay_day.py`; `results/replay_20200210.json` | Executable runs; numerical reproduction fails. Cause unresolved. |
| Sensor coverage/depth/clock performance | `analysis/sensor_sensitivity.py`; pilot outputs once complete | Exploratory one-day random holdout only. Not evidence of regional robustness or a tuned independent test. |
| Literature identity | `reports/reference_metadata.json`; `analysis/verify_references.py` | 17 DOI metadata records verified; substantive review focused, not systematic. |
| Author roles, permissions, ethics, funding | Inherited declarations | Require author confirmation; draft does not assert final approval. |
| Absolute regional volume accuracy or global conservation | No adequate supporting experiment | Unsupported; not claimed. |
| Road-class, OD-demand and seed robustness | No completed valid experiments | Open. No OSM class mapping or stochastic ensemble supplied. |

The article is an internal draft with visible limitations. Successful LaTeX
compilation does not change the scientific status of any row above.
