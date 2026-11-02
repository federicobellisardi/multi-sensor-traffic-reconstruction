# Regional traffic model

**Data-driven regional traffic simulation from heterogeneous mobility sources** (target: EPJ Data Science).

| Path | Content |
|---|---|
| `analysis/` | Pipeline: demand, route choice, detector correction, assessment, figures and tables |
| `results/` | Aggregate results of the final configuration; link-level outputs derived from proprietary data stay in `results/private/` (git-ignored) |
| `results/experiments/` | Experiments and the protocols written before them (`PROTOCOL*.md`) |
| `manuscript/` | `main.tex`, `references.bib`, `supplementary/main.tex`, generated `figures/` and `tables/` |
| `notes/` | Reference metadata |

Simulations and cluster workflow: `../hpc/README.md`.

Compile, from `manuscript/`: `latexmk -pdf main.tex` and `latexmk -pdf -jobname=supplementary supplementary/main.tex`.

## Final configuration

Demand without the destination code 000000000; model v2, with the relations of neighbouring provinces counted once (`NO_PROVINCE_COPY=1`); `k` = 1.5 (weekdays), 1.3 (weekends); radius 25 km; departures 45 min earlier; two rounds of province factors; alpha = 0.5, alpha_s = 0.25; correction depth 3. The settings are in `hpc/config.sh`.

## Where each figure and table comes from

Scripts are in `analysis/`; run them with `bash hpc/run_script.sh SCRIPT.py`. Figure numbers are those of the PDFs.

| Output (`manuscript/`) | Script | Main data (`results/`) |
|---|---|---|
| Pipeline schema | drawn in `main.tex` | -- |
| `fig1_inputs`, `fig2_demand` | `make_input_figures.py` | `corrected/input_figure_numbers.json` |
| `fig_level`, `fig_sources`, `fig_single`, `fig_factorial`, `fig_od` | `results_figures.py` | `demand/province_demand.json`, `demand/volume_validation.json`, `demand/single_road_error*.json`, `experiments/e2_factorial.json`, `experiments/od_pairing.json` |
| `fig3_reconstruction`, `fig4_gps`, `fig5_validation`, `fig5b_daytypes`, `fig7_volumes`, `fig8_distributions` | `make_figures.py` | `corrected/`, `private/` |
| `fig_detector_profiles` | `frozen_validation.py evaluate` (copied by `hpc/pipeline.sh`) | `demand/frozen_validation.json` |
| `figS_k_choice` | `k_choice_figure.py` | `demand/k_choice_curve.json` |
| `tables/loo`, `depth`, `routing_variants`, `routing_volumes` | `make_supp_tables.py` | `corrected/`, `routing/` |
| `tables/probe_strata`, `routing_shape` | `gps_fc.py` | `experiments/gps_fc.json`, `private/` |
| `tables/od_factorial`, `od_pairing`, `experiments_*` | `results_figures.py` | `experiments/` |
| `tables/od_decomposition` | `od_factor_decomposition.py` | `demand/od_factor_decomposition.json` |
| Tests T1--T4 | `validation_tests.py`, `gps_fc.py` | `corrected/validation_tests.json` |
| Diagnostics of single roads, route weights by link | `road_error_diagnosis.py`, `link_weight_test.py` | `experiments/road_error_diagnosis.json`, `experiments/link_weight_test.json` |
| 2021 without calibration detectors | `independent_2021.py` | `experiments/independent_2021.json` |
| Cost-weight grid of the SI | fixed table, from the first pass | `experiments/cost_grid_first_pass.json` |

## Scripts by stage

`analysis/` stays a flat folder, because the scripts import each other and `hpc/` calls them by name.

| Stage | Scripts |
|---|---|
| Inputs | `carto_geojson.py`, `osm_road_class.py`, `build_coils_table.py`, `build_node_scores.py`, `gps_link_speeds.py`, `od_clock_check.py` |
| OD and demand | `build_od_configs.py`, `od_matrix.py`, `remove_od_code.py`, `od_province_duplication.py`, `od_coverage.py` |
| Calibration | `calibrate_demand.py`, `demand_scaling.py`, `demand_scan_eval.py`, `radius_scan.py`, `departure_shift_test.py`, `province_demand.py`, `k_choice_figure.py` |
| Route choice and GPS | `routing_variants.py`, `routing_grid.py`, `compare_routing.py`, `gps_fc.py`, `gps_validation_split.py`, `link_weight_test.py` |
| Validation | `frozen_validation.py`, `volume_validation.py`, `volume_check.py`, `independent_2021.py`, `validation_tests.py`, `detector_baselines.py`, `delay_quarter.py` |
| Local correction | `reconstruct_and_validate.py`, `correction_fixed.py`, `depth_selection.py`, `distance_to_detector.py`, `loo_by_daytype.py`, `routing_correction_effect.py` |
| Single-road error | `single_road_error.py`, `road_error_diagnosis.py`, `detector_placement.py`, `direction_diagnosis.py` |
| Value of the OD | `source_value.py`, `od_factor_decomposition.py`, `od_pairing.py`, `od_pairing_d2.py`, `od_winter2023.py`, `od_tail_diagnostic.py`, `od_routing.py`, `od_length.py`, `od_length_factors.py`, `od_trip_length.py` |
| Final runs | `final_stage.py`, `final_experiments.py`, `final_experiments_eval.py` |
| Figures and tables | `make_figures.py`, `make_input_figures.py`, `make_supp_tables.py`, `results_figures.py` |
| Bibliography | `verify_references.py` |

Test T4 and its numbers on Forlì--Cesena are in `experiments/gps_fc.json`. `corrected/validation_tests.json` holds the same test outside the province, which the paper does not report.
