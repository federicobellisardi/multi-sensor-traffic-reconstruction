# OD information: pairing test, provincial duplication and winter 2023

Evaluated on 2026-11-02. The frozen model and its results are unchanged. All results here are exploratory, because the 2020 and 2021 detector data had been seen before registration.

## Conclusions
1. **The value of specific OD pairings on link counts is not determined.** Both radii are inconclusive under the registered rule, with power far below 80%. The tests do not show that pairings have no value.
2. **At the 25 km radius of the frozen model, pairings barely reach the detectors.** The measured signal is zero, and the median change at detectors (0.005 in log10) is below seed noise (0.009).
3. **At 10 km there is a weak signal in favour of the real pairs.** It is not enough to classify, and it comes from a run with about 40% too little volume.
4. **The provincial duplication is real but does not change the validation materially.** It should be disclosed.
5. **Winter 2023 cannot replace 2021.** Most of its apparent gain comes from which detectors are in the set.

## Pairing experiment
Protocol: `PROTOCOL_OD_PAIRING_D2.md`, amended by `PROTOCOL_OD_PAIRING_D2_AMENDMENT_1.md`. Results: `od_pairing_d2.json`, `od_pairing_d2_check.json`, `od_pairing_d2_controls.json`.

Phase 0, with 4 km bins: G1 passed; G2 passed (51.5-51.7% of agents moved); daily mean-distance gap 0.25%. The controls E1, E2 and E3 passed, with tau/sigma of at least 0.3 needed for 80% power.

All 16 simulations ended with exit code 0, none repeated. Each comparison pool has 168 detectors and 368 rows.

| Radius | b | 95% interval | tau/sigma | Power | Classification |
|---|---|---|---|---|---|
| r10 (primary) | 2.36 | [0.34, 4.40] | 0.072 | 0.15 | inconclusive |
| r25 (secondary) | not interpretable | [-414, 439] | 0.000 | 0.00 | inconclusive |

Reading of each radius:
- **r25.** The estimated signal is zero, so the denominator of b vanishes and the value -112 has no meaning. The empirical control confirms this: with a null truth the median b is 7.5.
- **r10.** The empirical controls behave as expected: median b 0.84 with a real truth, 0.03 with a null truth. The interval excludes 0, but under the Monte Carlo at this signal an interval excludes 0 in 5.8% of cases if b = 0 and in 17% if b = 1, a likelihood ratio of about 3. This is weak evidence. A b above 1 should not be read as an effect larger than the real pairs can produce: the interval includes 1.

Secondary, real minus null, four comparisons per radius (not used for classification):
- r10: dispersion lower with real pairs in all but one comparison, 2 of 4 intervals exclude zero; Spearman +0.012 to +0.014 in three comparisons and -0.001 in the fourth, all intervals include zero.
- r25: 1 of 4 dispersion intervals excludes zero, at its limit; Spearman differences within about 0.003, all intervals include zero.
- Winter 2023, set A (`winter2023_pairing.json`): r10 b = 2.29 [0.30, 4.70], power 0.14; r25 not interpretable, power 0.00. Both inconclusive. This is not a replication: same simulations and overlapping detectors.

### Interpretation
Facts: real and D2 differ little at detectors at 25 km, and more at 10 km (median change on all links 0.007 against 0.012-0.013 in log10).
Hypothesis, supported but not demonstrated: the 25 km endpoint spreading erases most of what a pairing could contribute beyond distance. The protocol allows the radius only as a candidate explanation, and here neither radius was classified.
Null D had a signal of 0.028 at r25 on the old runs, while D2 has none. This suggests that what null D changed there was mainly trip distance, though the arms and the bin definition differ.

### Limits
- Link counts only, no direct OD validation; routing and aggregation cannot be separated.
- One simulated day per day type; intra-municipal trips and random-end classes are outside the test.
- r10 is an intervention, with k not retuned. Its volume ratio is 0.58-0.64, against 0.80-0.95 at r25. r10 also shows lower dispersion and, on the 2020 half, higher Spearman than r25. These are not grounds to adopt it: it was not selected for that purpose, its level is wrong, and those comparisons were not registered.
- The r10 sensitivity is 0.011-0.012, near the seed noise of 0.007, so tau is itself poorly known and the power figure is approximate.

## Provincial duplication
Results: `../demand/province_duplication_count.json`, `../demand/province_duplication.json`. Script: `od_province_duplication.py`.

Cause: in `build_od_configs.build` the province rates are computed from all cells, while the destination, origin and local classes do not exclude those same cells. So some trips appear both in the province class and in a random-end class. The legacy configurations are reproduced exactly by the generator, so the feature is inherited and not a recent regression.

| Day | Copied agents | Share of agents | Province class share |
|---|---|---|---|
| Monday | 63,532 (rnd_rnd 41,212, rnd_dest 11,208, src_rnd 11,112) | 4.4% | 4.7% |
| Saturday | 68,388 | 5.0% | 5.4% |

The copy accounts for most of the roughly 67,000 first suspected; the province class itself stays.

Impact, from four unregistered runs with k not retuned; values are arm against frozen:

| Day, comparison | Spearman, no copy | Spearman, no province class | Frozen | Volume ratio, frozen to no copy |
|---|---|---|---|---|
| Monday, 2020 test half | 0.651 | 0.628 | 0.654 | 1.013 to 0.961 |
| Monday, 2021 | 0.634 | 0.608 | 0.623 | 1.101 to 1.054 |
| Saturday, 2020 test half | 0.646 | 0.643 | 0.651 | 1.001 to 0.942 |
| Saturday, 2021 | 0.627 | 0.620 | 0.625 | 1.030 to 0.978 |

Removing the copy changes Spearman by at most 0.011, with all intervals including zero, and dispersion by at most 0.003; one dispersion interval excludes zero (Saturday, 2021: slightly worse without the copy). Volume falls by 4-6%, which a retuned k would largely absorb. No correction was applied.

## Winter 2023
Protocol: `PROTOCOL_2023_WINTER.md`, registered before any simulated value was compared with a 2023 count. Results: `winter2023.json`. Calibration detectors excluded.

| Day, set | n | Spearman | sd log10 |
|---|---|---|---|
| Monday A, outside calibration | 122 | 0.743 [0.65, 0.81] | 0.237 [0.199, 0.276] |
| Monday B, exposed | 89 | 0.700 | 0.252 |
| Monday C, neither | 33 | 0.857 | 0.181 |
| Saturday A | 140 | 0.727 [0.63, 0.80] | 0.242 [0.204, 0.277] |
| Saturday B | 99 | 0.673 | 0.253 |
| Saturday C | 41 | 0.859 | 0.203 |

On common detectors the year changes little: Monday test half 0.630 in 2020 against 0.636 in 2023; Saturday test half 0.622 against 0.617; Monday 2021 0.625 against 0.636; Saturday 2021 0.625 against 0.683. The Monday volume is 39% above the 2023 counts and the Saturday 11% above, descriptive only.
Limits: dates and holidays of `winter` are undocumented; the values are means over many days, which alone lowers noise; set C is not untouched, since earlier rounds scanned k on 2022-24 means.

## Manuscript
Done, without changing any scientific claim: the description of intra-municipal trips (`main.tex`) and the coverage statistics (`main.tex`, `supplementary/main.tex`). Old statistics are preserved in `../demand/od_coverage_with_code_20261031.json`.

Recommended, for the author's decision:
1. **Abstract.** Replace "specific origin--destination pairs add no detectable value" with wording such as "the value of specific origin--destination pairs could not be determined from link counts". The present sentence is literally true, but a reader will take it as evidence of absence.
2. **Discussion, "Beyond distance, we detect no value" paragraph.** Keep it, and add that the test has power of at most 0.15 and that at 25 km the response of detectors to pairings is below seed noise.
3. **Sources table, OD row, and Supplementary S9.** Report D2, with amendment 1 and the weak r10 signal labelled inconclusive. Do not cite b = 2.36 without its power.
4. **Methods or Supplementary.** Disclose the duplication: 4.4-5.0% of agents, 4-6% of volume, no material change in ranking or dispersion in the unretuned runs. Keep the frozen model, because retuning would reopen every result.
5. **Winter 2023.** If included at all, supplementary only, with set A and set B separate and the common-detector comparison beside it. Keep 2021 as reported. Do not claim better performance in 2023.

## Deviations and undocumented choices
- Amendment 1: bins from 2 km to 4 km, after G2 failed and before any D2 run. The width was chosen knowing the share moved, and clears the threshold narrowly.
- The protocol does not state the number of generator sweeps; it was set to 3,000 plus 200 mean-correcting sweeps while testing the generator, before any D2 run.
- Within a 4 km bin trips can differ by up to 4 km, so a distance component in any effect cannot be excluded at the level of single trips.
- Measured tau is floored at zero when its estimate is negative, as in r25.
- The duplication impact runs were not preregistered.
- The earlier exploratory IV was abandoned, as stated in the protocol, because of its bias towards 1.
- r25 real runs are reused from `od_pairing`; the D2 and r10 runs were executed on the IFISC cluster with the frozen binary. Agreement across machines was not separately tested in this experiment.

## Not done
No correction of the duplication; no k retuning at r10; no direct OD validation; no repetition of E1-E3 with 4 km bins, since they depend on the old runs, not on the bin width; repository PDFs not rebuilt.
