#!/bin/bash
# Analyses of the article on the final simulations, beyond hpc/pipeline.sh (cluster job or interactive).
set -e
. "$(dirname "$0")/config.sh"
cd "$REPO"
export PATH=$ENV_DIR/bin:$PATH
A=model/analysis
python $A/frozen_validation.py evaluate
cp model/results/demand/frozen_validation.pdf model/manuscript/figures/fig_detector_profiles.pdf
python $A/detector_baselines.py
python $A/loo_by_daytype.py
python $A/gps_validation_split.py
python $A/source_value.py evaluate
python $A/source_value.py gps
python $A/validation_tests.py
python $A/make_figures.py
echo AFTER_FINAL_DONE; date
