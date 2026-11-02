# OD information: pairing test, provincial duplication and winter 2023

Model v2, evaluated on 2026-11-02. The v1 version of this report is at tag `frozen-v1`. All results here are exploratory, because the 2020 and 2021 detector data had been seen before registration.

## Conclusions
1. **The value of specific OD pairings on link counts is not determined.** Both radii are inconclusive under the registered rule, with power far below 80%. The tests do not show that pairings have no value.
2. **At the 25 km radius of the reported model, pairings barely reach the detectors.** The measured signal is close to zero (tau 0.005), and the median change at detectors (0.004-0.006 in log10) is below seed noise (0.009).
3. **At 10 km the estimate cannot be read as the value of the pairings.** Its interval excludes both 0 and 1, it is very different from v1, power is 0.11, and the run has about 40-45% too little volume.
4. **The provincial duplication was real and is corrected in v2.** It barely moves the reported model, but it changes the pairing arms.
5. **Winter 2023 cannot replace 2021.** Most of its apparent gain comes from which detectors are in the set.

## Pairing experiment
Protocol: `PROTOCOL_OD_PAIRING_D2.md`, amended by `PROTOCOL_OD_PAIRING_D2_AMENDMENT_1.md`. Results: `od_pairing_d2.json`, `od_pairing_d2_check.json`, `od_pairing_d2_controls.json`.

Phase 0, with 4 km bins: G1 and G2 passed (51.4-51.7% of agents moved); the mean-distance gap is 0.26-0.27%. The controls E1, E2 and E3 passed, with tau/sigma of at least 0.3 needed for 80% power. All 16 simulations ended with exit code 0. Each comparison pool has 168 detectors and 368 rows.

| Radius | b | 95% interval | tau/sigma | Power | Classification | v1 b, power |
|---|---|---|---|---|---|---|
| r10 (primary) | 4.58 | [2.39, 7.37] | 0.063 | 0.11 | inconclusive | 2.36 [0.34, 4.40], 0.15 |
| r25 (secondary) | not interpretable | [-233, 195] | 0.011 | 0.00 | inconclusive | not interpretable, 0.00 |

Reading of each radius:
- **r25.** The signal is near zero, so the denominator of b nearly vanishes and the value -13 has no meaning.
- **r10.** The registered rule gives inconclusive whatever the interval. Under the Monte Carlo at this signal, an interval excludes 0 in 6.3% of cases if b = 0 and in 14.3% if b = 1, a likelihood ratio of about 2.3, so exclusion of zero is weak evidence. The empirical controls give median b 0.78 with a real truth and -0.10 with a null truth, and with a real truth the interval covers 1 in 94% of cases. An interval at 2.39-7.37 is therefore not what real pairings acting alone should produce. Interpretation, not demonstrated: real and null pairs differ in some other way that correlates with the observed residual, or the small denominator makes the estimate unstable.

Secondary, real minus null, four comparisons per radius (not used for classification):
- r10: dispersion lower with real pairs in all four, 2 of 4 intervals exclude zero. Spearman +0.016 to +0.018 in three comparisons, 0.000 in the fourth; 2 of 4 intervals exclude zero, both on Saturday.
- r25: all 4 dispersion intervals include zero, with point estimates of at most +0.004. Spearman differences -0.004 to 0.000, all intervals include zero.
- Winter 2023, set A (`winter2023_pairing.json`): r10 b = 4.29 [2.34, 7.61], power 0.11; r25 not interpretable, power 0.00. Both inconclusive. This is not a replication: same simulations and overlapping detectors.

### Why the v2 values differ from v1
The v1 estimates must not be reused. In the N347 arms, almost all demand is assigned to specific pairs, so the duplicated province cells were a large part of what remained of the random-end traffic (`model/submission/FINAL_MODEL_AUDIT.md`). Without them, some detectors far from those pairs have almost no traffic. Residual sigma rises from 0.28 to 0.35 at r10 and from 0.33 to 0.41 at r25, while the reported model is almost unchanged.

Sensitivity of b to those detectors (ad hoc, not registered, not in the pipeline):

| Pool | r10 b | r25 b |
|---|---|---|
| All 168 detectors | 4.58 [2.37, 7.46] | -13 [-233, 195] |
| Without mean log10(obs/sim) of 1.0 or more | 3.62 [1.97, 5.54] (10 dropped) | 9.2 [-1.8, 22.9] (11 dropped) |
| Without 0.7 or more | 3.00 [1.50, 4.81] (19 dropped) | 8.9 [-1.0, 20.3] (15 dropped) |
| Without 0.5 or more | 3.03 [1.47, 5.00] (44 dropped) | 11.4 [1.5, 23.2] (34 dropped) |
| Without the 10 largest absolute contributions | 4.62 [2.76, 6.65] | 5.8 [-5.5, 19.2] |

The r10 estimate stays above 1 in every pool, so these detectors do not explain why b exceeds 1. Selecting on the residual also conditions on the outcome, so this table only describes sensitivity.

### Interpretation
Facts: real and D2 differ little at detectors at 25 km, and more at 10 km (median change on all links 0.007-0.008 against 0.013-0.015 in log10).
Hypothesis, supported but not demonstrated: the 25 km endpoint spreading erases most of what a pairing could contribute beyond distance. The protocol allows the radius only as a candidate explanation, and here neither radius was classified.

### Limits
- Link counts only, no direct OD validation; routing and aggregation cannot be separated.
- One simulated day per day type; intra-municipal trips and random-end classes are outside the test.
- The arm tested is not the reported model: at N347 the random-end classes hold 4.9% of Monday agents, against 72% in the reported model. A result here does not transfer directly to it.
- r10 is an intervention, with k not retuned. Its volume ratio is 0.55-0.60, against 0.77-0.92 at r25. r10 also shows lower dispersion than r25 in all four comparisons and higher Spearman on the 2020 half. These are not grounds to adopt it: it was not selected for that purpose, its level is wrong, and those comparisons were not registered.
- The r10 sensitivity is 0.012-0.017, near the seed noise of 0.011, so tau is itself poorly known and the power figure is approximate.

## Provincial duplication
Audit and correction: `model/submission/FINAL_MODEL_AUDIT.md`. Evidence for v1: `../demand/province_duplication_count.json`, `../demand/province_duplication.json` at tag `frozen-v1`.

In v1, the province rates were computed from all cells while the destination, origin and local classes did not exclude those cells, so some trips appeared twice: 63,532 agents on Monday (4.4%) and 68,388 on Saturday (5.0%) before scaling. The feature was inherited from the legacy configurations, not a recent regression. In v2, those cells stay out of the random-end classes. The province class itself is unchanged.

## Winter 2023
Protocol: `PROTOCOL_2023_WINTER.md`, registered before any simulated value was compared with a 2023 count. Results: `winter2023.json`. Calibration detectors excluded.

| Day, set | n | Spearman | sd log10 |
|---|---|---|---|
| Monday A, outside calibration | 122 | 0.743 [0.65, 0.81] | 0.238 [0.200, 0.278] |
| Monday B, exposed | 89 | 0.702 [0.57, 0.79] | 0.253 [0.204, 0.297] |
| Monday C, neither | 33 | 0.851 [0.72, 0.91] | 0.184 [0.135, 0.221] |
| Saturday A | 140 | 0.729 [0.63, 0.80] | 0.244 [0.205, 0.279] |
| Saturday B | 99 | 0.672 [0.53, 0.78] | 0.255 [0.207, 0.303] |
| Saturday C | 41 | 0.854 [0.72, 0.91] | 0.206 [0.149, 0.250] |

On common detectors the year changes little: Monday test half 0.625 in 2020 against 0.634 in 2023; Saturday test half 0.622 against 0.616; Monday 2021 0.637 against 0.656; Saturday 2021 0.635 against 0.687. The Monday volume is 39% above the 2023 counts and the Saturday 12% above, descriptive only.

Limits: dates and holidays of `winter` are undocumented; the values are means over many days, which alone lowers noise; set C is not untouched, since earlier rounds scanned k on 2022-24 means.

## Use in the manuscript
1. State: "The value of specific origin–destination pairings could not be determined from link-count observations with the statistical power available in this study."
2. Do not cite the r10 b without its power and the statement that it is not interpretable as the value of the pairings.
3. Winter 2023: Supplementary only, not as a replication, with sets A, B and C separate and the common-detector comparison beside them.

## Deviations and undocumented choices
- Amendment 1: bins from 2 km to 4 km, after G2 failed and before any D2 run. The width was chosen knowing the share moved, and clears the threshold narrowly.
- The protocol does not state the number of generator sweeps; it was set to 3,000 plus 200 mean-correcting sweeps while testing the generator, before any D2 run.
- Within a 4 km bin trips can differ by up to 4 km, so a distance component in any effect cannot be excluded at the level of single trips.
- Measured tau is floored at zero when its estimate is negative.
- The sensitivity table above was not registered; it was computed after seeing the v2 results.
- The earlier exploratory IV was abandoned, as stated in the protocol, because of its bias towards 1.
- r25 real runs are reused from `od_pairing` of v2.

## Not done
No k retuning at r10; no direct OD validation; no repetition of E1-E3 on v2 with separate bin widths; no test of whether the arms behave the same across machines.
