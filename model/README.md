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

Demand without the destination code 000000000; `k` = 1.4 (weekdays), 1.2 (weekends); radius 25 km; departures 45 min earlier; two rounds of province factors; alpha = 0.5, alpha_s = 0.25; correction depth 3. The settings are in `hpc/config.sh`.

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
