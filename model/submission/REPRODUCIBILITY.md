# Reproducibility

## Versions
| | Code and results | Simulations | Configurations |
|---|---|---|---|
| Reported model (v2) | branch `submission/epj-data-science` | `$WORK_ROOT/sim_runs_v2`, `$WORK_ROOT/nr_v2` | `conf_nocode_v2` |
| Earlier model (v1) | local tag `frozen-v1` | `$WORK_ROOT/sim_runs_nocode2`, `$WORK_ROOT/nr_2` | `conf_nocode` |

v1 is also archived in `$WORK_ROOT/archive_frozen_v1_20261102/`. Do not delete `nr_2`: the links in `sim_runs_nocode2` point to it.

## Commands
1. Environment and engine: `hpc/README.md`.
2. Everything in order, on the IFISC cluster: `bash hpc/run_all.sh`. It takes about four hours of wall time with free nodes.
3. Analysis only, from existing simulations: `bash hpc/pipeline.sh`, about 75 minutes as a cluster job. It rewrites `model/results`, `manuscript/tables` and `manuscript/figures`.
4. PDFs, from `model/manuscript/`: `latexmk -pdf main.tex`, then `latexmk -pdf -jobname=supplementary supplementary/main.tex`.

Steps 2 and 3 need the proprietary inputs, which are not distributed.

## What was run for the reported results
- `hpc/run_all.sh` on 2026-11-02, then six runs repeated after the correction of the duplicated provincial demand (`NO_PROVINCE_COPY=1` in `hpc/config.sh`), then the full pipeline: 47 steps, all with return code 0.
- `final_experiments` regression run: byte-identical to the final Monday simulation.
- Figure 7 was regenerated alone after its code changed. It uses the same data, adds `by_class` and `both_years` to `corrected/figure_numbers.json`, and has its own seed for the jitter and the bootstrap.

## Exploratory tests after the reported results
Protocol: `model/results/experiments/PROTOCOL_OD_ROUTING.md`. Run by hand, not in `hpc/pipeline.sh`:
- `od_routing.py`, `od_length.py`, `od_length_factors.py`: `jobs`, `one`, `evaluate` through `hpc/submit_stage.sh`, with `SIM_ENGINE=$WORK_ROOT/build_explore/sim_engine`. Outputs in `$SIM_RUNS/od_routing`, `od_length`, `od_length_factors`; results in `od_routing.json`, `od_length.json`, `od_length_factors.json`. `miss10` and `miss30` ran with the earlier binary.
- `od_trip_length.py` and `od_tail_diagnostic.py`, on existing runs.

**Engine.** `simulation_io.cpp` now skips sources without a location in `_sources.csv`. The rebuilt binary reproduces the final Monday link flows byte for byte; the other days were not compared. The reported results used the earlier binary, `$WORK_ROOT/build_ubuntu22.04/sim_engine`.

## Known limits
- **Resuming runs.** `demand_scaling.run` accepts an existing output without comparing configurations. Do not reuse a `SIM_RUNS` name or an `nr_<suffix>` directory for another model.
- **`od_pairing_check.json`.** It was not regenerated for v2. Its agent counts are those of v1; the distances and shares moved quoted in the Supplementary do not depend on the scale, but this was not rechecked by a rerun.
- **Null M at 347 municipalities.** It ended with a segmentation fault in an earlier configuration, probably the `_sources.csv` defect, and was not repeated on v2.
- **Short directories `nr_*`.** They were made for LOCALS-only runs after a crash attributed to long paths, which may be the same defect. Not tested.
- **Random generator.** `minimocas/src/lib/pawn.h:31` holds a `static std::mt19937` in a header, so the seed does not reach all draws. Its effect on the variation between seeds was not measured, and that variation enters the power analysis of the pairing test.
- **`direction_diagnosis.py`.** It is not in the pipeline and still reads `source_value/no_od`.
- **Sensitivity table of the pairing report.** It was computed ad hoc and is not in the pipeline.
- **Code layout.** `model/analysis/` was not split into stage folders. Moving the scripts would need a full pipeline check at the last moment and would change no result, so `model/README.md` has a map by stage instead.
