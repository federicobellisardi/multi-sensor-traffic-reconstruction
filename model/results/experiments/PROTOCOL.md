# Experiments on the frozen model: protocol

Written on 2026-11-01, before any of these runs. Nothing here changes the frozen model or the manuscript values; any
outcome is reported as it is. Daily volumes from distinct-agent counts, both directions. Test half and 2021 as in the
manuscript. Paired bootstrap over detectors, 2,000 resamples, 95% intervals. All exploratory: the test half and 2021 have been seen.

## E1 Response to a real change in demand (lockdown)
Demand: mean TIM OD by weekday, 16-28 March 2020, same k, province factors and routing; template as the frozen model.
Observed change of a detector: mean daily volume 16-20, 23-27 March (weekdays), 21, 22, 28 March (weekends; 29 March is
excluded for the clock change), over the same volume on the February groups of the model. Isolated gaps are read as zero
(at most 20 intervals, none longer than 4), in both periods, since quiet nights are recorded as missing; a mean needs at
least 2 valid weekdays or 1 valid weekend day. Detectors of the test half.
Simulated change: Monday or Saturday March run over the same run of February.
Predictors: P_dem, the change in total agents (demand only, no simulation, no detector); P_det, the median observed change
of the calibration detectors (it has seen March counts).
Error: median |log10(predicted change / observed change)|.
Rule: the simulation adds spatial information on change if the interval of (error simulation - error P_dem) is below zero,
on either day type. Beating P_det is reported, and not required. Value of relations: same with the March run without relations.

## E2 Relations with the regional pattern kept
Run without relations with node scores times sqrt(province factor), which gives a trip the geometric mean of the
factors of its ends, as in the model; total agents as in the model. With the runs that exist this completes the 2x2 design.
Rule as in the manuscript: relations supported if on test half or 2021, Spearman interval above zero or dispersion interval below
zero. Interaction: paired bootstrap of the difference of differences. Limit: the pattern enters through random ends only.

## E3 How many detectors
k: on the existing k grid, 200 random subsets of 10, 25, 50 calibration detectors: the k chosen, and its loss on the test half.
Province factors: 3 random stratified subsets of 25 and 50 calibration detectors, two rounds as in the model; dispersion and median
error on test half and 2021, against 100 detectors.
Correction: a fixed 20% of complete detectors as target; 25, 50, 75, 100% of the rest, nested, 5 repeats; 10 Feb 2020 and 28 June 2021. Descriptive.

## E4 Route choice on the final model
Variants V0-V5 of the manuscript, with factors, Monday and Saturday. Selection metric as before: Spearman with GPS counts, Forli-Cesena.
The selected variant stands if no other has an interval (paired, over links) of the difference above zero, on both days.
Separation: D1 (default speeds, usage cost and weights) against V0, V1 (GPS speeds only) against V0, V6 against both.
Transfer: T1 (class weights from GPS counts outside Forli-Cesena) against V0 and V6, at detectors inside the province.
Grid of (alpha, alpha_s) as in the supplement, calibration detectors, on the final model; same rule as there.
Metrics at detectors: test half and 2021, outside Forli-Cesena.

## E5 Scale k with province factors
Grid 0.7-1.2 by day type, calibration detectors. The value stands if it is the minimum of the grid. Paired intervals as in Fig. S1.

## E6 More relations with province factors
N = 100, multiplier 1.0, 1.15, 1.3, chosen as k; calibration half; same "beats" rule as without factors; 2021 only if it beats.
Direction of travel: same measure and same rule as before, on the test half.

## E7 Variability between runs
Saturday with seeds 2, 3, 4. Range of the metrics on test half and 2021, with the Monday values that exist.

## E8 No new simulation
Spatial block bootstrap of the GPS timing differences (blocks: province, and a 20-km grid). Detector-link direction check: observed split
against simulated split, by detector. Detector 153: why the link has no flow.

## Not possible
Another region: no data. GPS speeds from other provinces: raw traces exist only for Forli-Cesena.
