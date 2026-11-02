# Value of OD pairings, null D2 and endpoint radius: protocol

Registered on 2026-11-02, before the D2 generator was written and before any run below. Frozen model unchanged; `od_pairing.json` and its runs are preserved.
All 2020 and 2021 detector data have been seen, and an unregistered projection analysis was read on the N347 and N50 runs of `PROTOCOL_OD_PAIRING.md`. Every result here is exploratory.

## Question
Given O_i(t) and D_j(t), does the specific municipal pairing improve the prediction of detector counts, and does the 25 km endpoint radius hide it?

## Why a new protocol
The earlier twin test uses a truth without observation error and overstates power. If a permutation adds variance tau^2 to a residual of variance sigma^2, then the change in dispersion is about tau^2/(2 sigma), with standard error about tau/sqrt(n).
Null D moves 51-67% of agents and lengthens trips by 11-14%. At 25 km a relation of 12 km becomes about 20 km, and its destination distribution overlaps strongly with that of an alternative at the same distance.

## Arms (N347, Monday 2020-02-10 and Saturday 2020-02-15)
Demand scale k, province factors, route cost, classes with a random end and every other parameter as `N347_r20_x` of `od_matrix.py`. Random-end classes keep 25 km.
- r25: `real_s1`, `real_s2` reused from `od_pairing/N347_real_s*` (the name r20 there means the selected radius, 25 km). New: D2 reps 0, 1, 2.
- r10: real with engine seeds 1, 2; D2 reps 0, 1, 2. Relation ends and origin spreading at 10 km, with the existing fallback to 25 km when an end has fewer than 3 nodes within the radius (`MIN_NODES`).
16 new simulations. Engine seeds of D2: 11, 12, 13. The destination permutation of a rep is the same at both radii. Outputs: `$SIM_RUNS/od_pairing_d2/`.
A run is repeated only if it crashes, with the same seed, and this is reported. No arm, radius or seed is changed after results are read.

## Null D2
Within each 15-min interval, destinations are exchanged among the relation agents, so O_i(t), D_j(t) and the total are exact.
An agent stays in the 2 km bin of its real centroid distance (0-2, ..., 98-100, >100 km) and never has a self-pair. Afterwards, swaps that keep these constraints and reduce the gap in mean distance are applied until the daily trip-weighted mean is within 1% of the real one.
Other sources are identical to the real arm.

## Phase 0: must pass before the simulations
G1. In all reps and both days: O_i(t), D_j(t) and class totals identical; distance histogram by interval identical; daily mean distance within 1%; no self-pairs; non-relation sources identical; configuration equal outside `sources`.
G2. Share of agents moved at least 50%.
E1. Negative control (Monte Carlo, truth b = 0, tau/sigma >= 0.2): |median b| <= 0.2 and interval excluding zero in at most 10% of replicates.
E2. Positive control (truth b = 1, tau/sigma >= 0.2): |median b - 1| <= 0.2 and interval covering 1 in at least 90% of replicates.
E3. Some tau/sigma <= 0.5 reaches power of at least 80% (0.5 is about what null M reaches). The tau/sigma needed is written down before the runs.
The controls use real detector sets, residual vectors resampled by detector with their within-detector correlation, and measured seed noise.
A failure stops the simulations and is reported.

## Primary analysis
Estimand: b in log10(obs) - log10(E[null]) = a + b (log10(E[real]) - log10(E[null])). b = 1 favours the real pairs, b = 0 the null.
Cross-fitted instrumental variable estimator, to remove the seed and permutation noise of both real and null: for null rep k and ordered seeds (u, v), y = log obs - mean of the other nulls, x = log real_u - mean of the other nulls, z = log real_v - null k; all demeaned within a comparison. b = sum(z y) / sum(z x) over all k and orders.
The IV written in the unregistered analysis (instrument and regressor sharing the same null mean) does not remove the null noise, which pulls b towards 1, and is abandoned. Its value is not used.
Comparisons pooled: test half of 2020 and 2021, Monday and Saturday. Rows with zero flow in any arm are excluded.
Interval: percentile, 2,000 bootstrap resamples of detectors (clusters), seed 20261110.
Primary: r10. r25 is secondary, also because it is the radius of the frozen model. Mechanism: tau and b compared across radii, descriptively.

## Power after the runs
Measured tau_signal^2 = var(z-type cross product estimate), with sigma the residual sd of the same arm. Power of the rule below is read from the Monte Carlo at these values.

## Classification, applied to each radius
Power below 80%: inconclusive, whatever the interval, and the interval is reported.
Power at least 80%:
- supported: interval excludes 0 and includes 1;
- unsupported (no detectable value on link counts): interval includes 0 and excludes 1;
- inconclusive: interval includes both;
- anomalous, treated as inconclusive: interval excludes both.
If r10 is supported and r25 is not, the radius is a candidate explanation, not a demonstration.

## Secondary, not used for classification
By comparison and pooled: change in dispersion and Spearman, real seed 1 minus null mean, paired bootstrap. Volume ratio. Sensitivity at detectors and on all links. Empirical controls after the runs: truth = null rep or real seed plus resampled residuals (expected b near 0 and 1).

## Limits known in advance
Link counts only; no direct OD validation is possible, the raw Viasat traces are not available. One simulated day per day type. N347 and r10 are interventions, not the frozen model. Trips within a municipality and random-end classes are outside the test. Results cannot separate routing from aggregation.
Nothing here changes the frozen model or main claims before evaluation.
