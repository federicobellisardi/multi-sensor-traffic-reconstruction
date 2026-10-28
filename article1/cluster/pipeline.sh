#!/bin/bash
# Analysis pipeline on the final scaled simulations (cluster job submitted by submit.sh; also runs
# interactively). Expects SIM_RUNS and MOVER; CARTO_API_KEY is read from $MOVER/carto_key if present.
set -e
REPO=$(cd "$(dirname "$0")/../.." && pwd)
cd "$REPO"
export PATH=$MOVER/env/bin:$PATH NPROC=${NPROC:-8}
[ -f "$MOVER/carto_key" ] && export CARTO_API_KEY=$(cat "$MOVER/carto_key")
A=article1/analysis
for v in V6_scaled V0_scaled; do
  n=$(ls "$SIM_RUNS/demand/$v"/sim_*_barriers_*.csv | wc -l)
  echo "$v: $n simulated days with barrier output"
done
echo "== determinism check and relabelling"; date
python $A/demand_scaling.py relabel
for v in V6_scaled V0_scaled; do [ "$(ls "$SIM_RUNS/demand/$v"/sim_*_barriers_*.csv | wc -l)" -eq 15 ]; done
echo "== V0: assimilation and validation (routing-shape table)"; date
SIM_DIR=$SIM_RUNS/demand/V0_scaled OUT_DIR=article1/results/baseline_v0 python $A/reconstruct_and_validate.py assimilate
SIM_DIR=$SIM_RUNS/demand/V0_scaled OUT_DIR=article1/results/baseline_v0 python $A/reconstruct_and_validate.py validate
echo "== V6: assimilation, validation, distance, routing comparison"; date
python $A/reconstruct_and_validate.py assimilate
python $A/reconstruct_and_validate.py validate
python $A/distance_to_detector.py
python $A/compare_routing.py
echo "== leave-one-detector-out"; date
python $A/reconstruct_and_validate.py loo
echo "== propagation depth"; date
python $A/sensitivity_fixed.py
echo "== volume checks"; date
for y in 2020 2021; do for k in raw assim; do python $A/volume_check.py "$SIM_RUNS/demand/V6_scaled" $y $k; done; done
echo "== figures and tables"; date
python $A/make_input_figures.py
python $A/make_figures.py
python $A/make_supp_tables.py
echo PIPELINE_DONE; date
