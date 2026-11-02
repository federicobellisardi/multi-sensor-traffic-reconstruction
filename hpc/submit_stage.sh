#!/bin/bash
# Submits the unfinished simulations of one script: bash hpc/submit_stage.sh SCRIPT [TIME] [MEM]
export PATH=/common/slurm/bin:$PATH
R=$(cd "$(dirname "$0")/.." && pwd)
. "$R/hpc/config.sh"
mkdir -p "$LOGS"
Q=$(squeue -u "$USER" -h -o %j)
cd "$R/model/analysis"
"$PY" "$1.py" jobs $4 2>/dev/null | while read -r a b c; do
  j=nc_$1_${a}_${b}_${c}
  echo "$Q" | grep -qx "$j" && continue
  run -t "${2:-3:00}" -c 2 -m "${3:-8}" -j "$j" -o "$LOGS/$j.out" -e "$LOGS/$j.err" bash "$R/hpc/run_script.sh" "$1.py" one $a $b $c < /dev/null | tail -1
done
