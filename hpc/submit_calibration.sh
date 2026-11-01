#!/bin/bash
# Submit the calibration simulations of Part A and the depth selection of Part B through `run` (Slurm).
#   bash hpc/submit_calibration.sh demand     drop-one-class and k-grid runs   (model/analysis/calibrate_demand.py)
#   bash hpc/submit_calibration.sh routing    (alpha_we, alpha_speed) grid     (model/analysis/routing_grid.py)
#   bash hpc/submit_calibration.sh depth      cross-validated propagation depth (model/analysis/depth_selection.py)
# Only the simulations that are not finished yet are submitted (the scripts' `jobs` lists them).
# Evaluation afterwards: python model/analysis/<script>.py evaluate   (depth: summary is printed by the job).
# Override RUN to use another submitter with the same options (-t -c -m -j -o -e).
set -e
. "$(dirname "$0")/config.sh"
RUN=${RUN:-run}
mkdir -p "$LOGS"
cd "$REPO"
what=${1:?usage: submit_calibration.sh demand|routing|depth}

sims() {  # script
  "$PY" "model/analysis/$1.py" jobs | while read -r name day; do
    $RUN -t 1:00 -c 2 -m 6 -j "$1_${name}_${day}" -o "$LOGS/$1_${name}_${day}.out" -e "$LOGS/$1_${name}_${day}.err" \
         bash "$REPO/hpc/job.sh" python "model/analysis/$1.py" one "$name" "$day" < /dev/null
  done
}

case $what in
  demand)  sims calibrate_demand ;;
  routing) sims routing_grid ;;
  depth)   $RUN -t 4:00 -c 8 -m 32 -j depth_selection -o "$LOGS/depth_selection.out" -e "$LOGS/depth_selection.err" \
                bash "$REPO/hpc/job.sh" python model/analysis/depth_selection.py run ;;
  *) echo "unknown: $what"; exit 1 ;;
esac
