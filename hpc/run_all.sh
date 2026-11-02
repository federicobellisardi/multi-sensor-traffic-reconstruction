#!/bin/bash
# All simulations and analyses of the paper, in order (cluster with the Slurm wrapper `run`): bash hpc/run_all.sh
export PATH=/common/slurm/bin:$PATH
R=$(cd "$(dirname "$0")/.." && pwd)
. "$R/hpc/config.sh"
export PATH=$ENV_DIR/bin:$PATH
J="bash $R/hpc/run_script.sh"
wait_jobs() { while [ "$(squeue -u "$USER" -h -o %j | grep -c '^nc_')" != 0 ]; do sleep 60; done; }
sub() { bash "$R/hpc/submit_stage.sh" "$@" | grep -c Submitted; }
cd "$R"
$J remove_od_code.py 2>&1 | grep -v PROJ | cut -c1-120
echo "== radius and k"; sub radius_scan; wait_jobs; sub radius_scan; wait_jobs
$J radius_scan.py refine > "$LOGS/refine.log" 2>&1; echo "refine RC $?"
python3 - <<PY
import json
d=json.load(open('$RESULTS_DIR/demand/radius_scan_refined.json'))
r=d['selected_radius'];k=d['k_by_day_type'][str(r)]
open('$RESULTS_DIR/demand/selected_radius','w').write(str(r))
json.dump({'k':k['2020-02-10'],'k_weekend':k['2020-02-15'],'criterion':'minimum per day type of the mean squared log10(sim/obs) on the calibration half, without code 000000000, alpha_s 0.25; radius_scan.py refine','coils_calibration':100,'coils_test':97,'seed':20261028},open('$RESULTS_DIR/demand/k_choice.json','w'),indent=1)
print('radius',r,'k',k)
PY

echo "== shift and runs without factors"; sub final_stage 3:00 8 shift; sub final_stage 3:00 8 before; wait_jobs
$J final_stage.py shift 2>&1 | grep -v PROJ | grep -E 'difference_pp|below_zero|-?[0-9]\.[0-9]+,?$' | cut -c1-60
python3 -c "
import json;d=json.load(open('$RESULTS_DIR/demand/departure_shift.json'))
assert d['2020-02-10']['below_zero'],'SHIFT RULE NOT MET ON MONDAY'"; [ $? = 0 ] || { echo STOP_SHIFT; exit 2; }
echo "== factors"; $J province_demand.py factors 1 2>&1 | grep -v PROJ | cut -c1-200; sub final_stage 3:00 8 round1; wait_jobs
$J province_demand.py factors 2 2>&1 | grep -v PROJ | cut -c1-200; sub final_stage 3:00 8 round2; wait_jobs
$J final_stage.py relabel > "$LOGS/relabel.log" 2>&1
$J province_demand.py evaluate > "$LOGS/pd_eval.log" 2>&1; echo "evaluate RC $?"; $J province_demand.py confirm > "$LOGS/pd_conf.log" 2>&1; echo "confirm RC $?"
python3 - <<PY
import json,shutil
d=json.load(open('$RESULTS_DIR/demand/province_demand.json'))
ok=d['gain_on_test'] and d['confirmation_2021']['adopted']
print('factors adopted',ok)
if ok: shutil.copy('$SIM_RUNS/province_demand/factors_round2.json','$RESULTS_DIR/demand/province_factors.json')
PY
echo "== final simulations and experiments"
$J frozen_validation.py config > /dev/null 2>&1
for f in "$SIM_RUNS"/final_q15/sim_*.json; do j=nc_q15_$(basename "$f" .json); run -t 3:00 -c 2 -m 8 -j "$j" -o "$LOGS/$j.out" -e "$LOGS/$j.err" bash "$R/hpc/run_engine.sh" "$f" < /dev/null | tail -1 | grep -c Sub; done
sub final_stage 3:00 8 final; sub source_value 3:00 8; sub od_pairing 3:00 12; sub link_weight_test 3:00 8
for i in 1 2 3; do sub final_experiments 3:00 12; wait_jobs; done
# OD pairing, null D2: controls and generator checks before its runs (PROTOCOL_OD_PAIRING_D2.md, amendment 1)
run -t 3:00 -c 2 -m 16 -j nc_d2_controls -o "$LOGS/d2_controls.log" -e "$LOGS/d2_controls.err" bash "$R/hpc/run_script.sh" od_pairing_d2.py controls < /dev/null | tail -1
run -t 3:00 -c 2 -m 16 -j nc_d2_check -o "$LOGS/d2_check.log" -e "$LOGS/d2_check.err" bash "$R/hpc/run_script.sh" od_pairing_d2.py check < /dev/null | tail -1; wait_jobs; tail -1 "$LOGS/d2_check.log"
if tail -1 "$LOGS/d2_check.log" | grep -q 'passed True'; then sub od_pairing_d2 3:00 8; wait_jobs; else echo STOP_D2; fi
cd model/analysis; for s in final_experiments od_pairing od_pairing_d2 source_value; do echo "$s missing: $($PY $s.py jobs 2>/dev/null | wc -l)"; done; echo "final missing: $($PY final_stage.py jobs final 2>/dev/null | wc -l)"; cd "$R"
cmp "$SIM_RUNS"/final_experiments/regression/sim_200210_uniq_*.csv "$SIM_RUNS"/demand/V6_scaled/sim_200210_uniq_*.csv && echo REGRESSION_IDENTICAL
echo "== analysis"; run -t 16:00 -c 8 -m 32 -j nc_pipeline -o "$LOGS/pipeline.out" -e "$LOGS/pipeline.err" bash "$R/hpc/pipeline.sh" < /dev/null | tail -1; wait_jobs
grep -E '^RC' "$LOGS/pipeline.out" | grep -v 'RC 0'; tail -1 "$LOGS/pipeline.out"
echo FULL_DONE
