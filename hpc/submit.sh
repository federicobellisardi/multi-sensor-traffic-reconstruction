#!/bin/bash
# Submit the final simulations and the analysis pipeline through the IFISC wrapper `run` (Slurm).
#   bash hpc/submit.sh
# One job per simulation (one run per weekday for V6 and V0, plus 17 Feb 2020 for the determinism
# check), then one job that waits for all of them and runs hpc/pipeline.sh.
# Override RUN to use another submitter with the same options (-t -c -m -j -o -e -d).
set -e
. "$(dirname "$0")/config.sh"
RUN=${RUN:-run}
mkdir -p "$LOGS"
cd "$REPO"

ids=()
for job in $("$PY" -c "import sys; sys.path.insert(0, 'model/analysis'); import demand_scaling as D; print(' '.join(f'{n},{d}' for n, d in D.final_jobs()))"); do
  name=${job%,*}; day=${job#*,}
  out=$($RUN -t 3:00 -c 2 -m 6 -j "sim_${name}_${day}" -o "$LOGS/sim_${name}_${day}.out" -e "$LOGS/sim_${name}_${day}.err" \
        bash "$REPO/hpc/job.sh" python model/analysis/demand_scaling.py one "$name" "$day")
  echo "$out"
  id=$(echo "$out" | grep -oE '[0-9]+' | tail -1)
  [ -n "$id" ] || { echo "cannot read the job id from: $out"; exit 1; }
  ids+=("$id")
done
echo "simulation jobs: ${ids[*]}"
# the pipeline starts only if every simulation job ended successfully (afterok on the full list)
deps=$(IFS=:; echo "${ids[*]}")
$RUN -t 8:00 -c 8 -m 32 -j model_pipeline -d "$deps" -o "$LOGS/pipeline.out" -e "$LOGS/pipeline.err" \
    bash "$REPO/hpc/job.sh" bash hpc/pipeline.sh
