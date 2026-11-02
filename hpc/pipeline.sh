#!/bin/bash
# Analysis of the final simulations (cluster job). Every step is attempted and its outcome logged.
. "$(dirname "$0")/config.sh"; cd "$REPO"
export PATH=$ENV_DIR/bin:$PATH NPROC=${NPROC:-8}
A=model/analysis
step() { echo "== $*"; date; "$@" > "$LOGS/step_$(echo "$*" | tr -c 'a-zA-Z0-9_' '_' | cut -c1-70).log" 2>&1; echo "RC $? : $*"; }
step python $A/demand_scaling.py relabel
export OUT_DIR=$RESULTS_DIR/baseline_v0 PRIV_DIR=$RESULTS_DIR/private/baseline_v0 SIM_DIR=$SIM_RUNS/demand/V0_scaled; mkdir -p "$PRIV_DIR"
step python $A/reconstruct_and_validate.py assimilate
step python $A/reconstruct_and_validate.py validate
unset OUT_DIR PRIV_DIR SIM_DIR
step python $A/reconstruct_and_validate.py assimilate
step python $A/reconstruct_and_validate.py validate
step python $A/distance_to_detector.py
step python $A/compare_routing.py
step python $A/reconstruct_and_validate.py loo
step python $A/routing_correction_effect.py
step python $A/depth_selection.py run
step python $A/depth_selection.py summary
step python $A/volume_validation.py
step python $A/frozen_validation.py evaluate
step python $A/detector_baselines.py
step python $A/loo_by_daytype.py
step python $A/gps_validation_split.py
step python $A/source_value.py evaluate
step python $A/source_value.py gps
step python $A/validation_tests.py
step python $A/single_road_error.py
step python $A/single_road_error.py adopted
step python $A/detector_placement.py
step python $A/od_coverage.py
step python $A/k_choice_figure.py
step python $A/gps_fc.py
for e in e2 e3k e3f e3c e4 e5 e6 e7; do step python $A/final_experiments_eval.py $e; done
step python $A/od_pairing.py evaluate
step python $A/od_pairing_d2.py evaluate
step python $A/od_winter2023.py frozen
step python $A/od_winter2023.py pairing
step python $A/independent_2021.py
step python $A/road_error_diagnosis.py
step python $A/link_weight_test.py evaluate
step python $A/od_factor_decomposition.py
step python $A/results_figures.py
step python $A/make_figures.py
step python $A/make_input_figures.py
step python $A/make_supp_tables.py
step python $A/gps_fc.py
step python $A/results_figures.py
cp "$RESULTS_DIR/demand/frozen_validation.pdf" "$REPO/model/manuscript/figures/fig_detector_profiles.pdf"
cp "$RESULTS_DIR/demand/frozen_validation.png" "$REPO/model/manuscript/figures/fig_detector_profiles.png"
echo PIPELINE_DONE; date
