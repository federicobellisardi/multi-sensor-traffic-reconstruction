#!/bin/bash
# Submit the final simulations and the analysis pipeline to the IFISC cluster (wrapper `run` over Slurm).
#   cd /data/workspaces/fbellisardi/mover_data/covid_hep && bash article1/cluster/submit.sh
# One job per simulation (one run per weekday for V6 and V0, plus 17 Feb 2020 for the determinism
# check), then one job that waits for all of them and runs article1/cluster/pipeline.sh.
set -e
REPO=$(cd "$(dirname "$0")/../.." && pwd)
MOVER=${MOVER:-$(dirname "$REPO")}
export SIM_RUNS=${SIM_RUNS:-$MOVER/sim_runs}
PY=$MOVER/env/bin/python
LOGS=$MOVER/logs
mkdir -p "$LOGS"
cd "$REPO"

ids=()
for job in $($PY -c "import sys; sys.path.insert(0, 'article1/analysis'); import demand_scaling as D; print(' '.join(f'{n},{d}' for n, d in D.final_jobs()))"); do
  name=${job%,*}; day=${job#*,}
  out=$(run -t 3:00 -c 2 -m 6 -j "sim_${name}_${day}" -o "$LOGS/sim_${name}_${day}.out" -e "$LOGS/sim_${name}_${day}.err" \
        env SIM_RUNS="$SIM_RUNS" OMP_NUM_THREADS=2 "$PY" article1/analysis/demand_scaling.py one "$name" "$day")
  echo "$out"
  ids+=($(echo "$out" | grep -oE '[0-9]+' | tail -1))
done
first=${ids[0]}; last=${ids[${#ids[@]}-1]}
echo "simulation jobs: ${ids[*]}"
run -t 8:00 -c 8 -m 32 -j article1_pipeline -d "$first:$last" -o "$LOGS/pipeline.out" -e "$LOGS/pipeline.err" \
    env SIM_RUNS="$SIM_RUNS" MOVER="$MOVER" bash article1/cluster/pipeline.sh
