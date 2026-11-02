# Re-run without the destination code 000000000: protocol

Written on 2026-11-01, before these runs. Decision of the user. The earlier results stay in model/results and $WORK_ROOT/sim_runs.

Demand: cells with destination code 000000000000 (name N/A) are removed from the mean OD of 13 Jan - 23 Feb 2020, by the same generator; no other change.
Not re-opened (structural choices kept): origin spreading, relations placed as before, population scores, no intra-municipal trips, closed links, 50 municipalities, route variant V6 unless its test below fails.
Re-estimated with the same rules as before, in this order, on the calibration half:
1. Radius (15, 20, 25, 30 km) and k by day type, grid 0.9-1.8. Minimum loss.
2. Departure shift: rule as in departure_shift_test.py. Applied only if met as before: kept at 45 min if met on the Monday.
3. Province factors, two rounds; adopted if the 95% interval of the change in dispersion is below zero on the test half and then in 2021. If not, the final model has no factors.
Then: final simulations, correction, GPS validation (Forli-Cesena), depth, leave-one-out, final tests, predictors, experiments on OD, routing, subsets, seeds.
If a rule selects a value different from before, it is applied without further choice. Rounds outside this list stay reported as made with the code in the data.
All validation data have been seen: results are exploratory about this change.

## Second pass (2026-11-01)
In the first pass (model/results_nocode) the rule of the cost-weight grid selected alpha = 0.5, alpha_s = 0.25 on the calibration half (dispersion 0.189 to 0.184, [-0.008, -0.001]; 1 of 7 variants, no correction for multiplicity). On independent detectors the interval reached zero in all four comparisons. The rule was applied by decision of the user. All steps are repeated with this route cost; the grid is reported, and the route cost is not opened again.

Note on locations (2026-11-02): this pass is now the content of model/results. Earlier passes are archived outside the repository.
