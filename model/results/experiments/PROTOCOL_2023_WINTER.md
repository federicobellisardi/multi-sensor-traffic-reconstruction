# Winter 2023 detectors, supplementary temporal comparison: protocol

Registered on 2026-11-02, before any simulated value was compared with a 2023 count. So far only the structure of the file and the number of complete detectors have been read.
This is supplementary temporal validation, not independent confirmation. It does not replace the 2021 results, which stay reported, and it changes no parameter of the model.

## Data
`data/coils_ave_230101-000000_231231-234500.csv`, season `winter`, rows `wday` Mon and Sat. Daily volume of a detector: sum over the 96 intervals and both directions; a detector enters only if all are present.
The dates in `winter` and the handling of holidays are not documented in the file: this is a limit. The values are means over many days, unlike the single days of 2021, so a better number can come from less noise, and comparisons across years are descriptive only.

## Simulation
Raw frozen model, without correction: `$SIM_RUNS/demand/V6_scaled`, Monday 2020-02-10 and Saturday 2020-02-15, demand of early 2020, as `od_factor_decomposition.py`.

## Detector sets
Calibration detectors are excluded everywhere (split of `demand_scan_eval.split`).
- A, primary: all others complete in the 2023 table.
- B, exposed: subset of A in the 2020 test half or in the 2021 sets.
- C: subset of A in neither.
Earlier demand rounds used averages of 2022-24 to scan k (`HANDOFF.md`), and the correction code reads these tables, so even set C is not untouched. The Monday and Saturday tables also share detectors.

## Metrics, by day type and set
Primary: Spearman correlation and sd of log10(sim/obs), for detectors with simulated flow. Also median |log10(sim/obs)| and share within a factor of two.
Volume ratio is descriptive only: k was fixed on February 2020 and earlier work found the 2020 counts about 24% above the 2022-24 means on common detectors.
Intervals: percentile, 2,000 bootstrap resamples of detectors, seed 20261111.
Context, descriptive: the same metrics on the detectors of A shared with the 2020 test half and with 2021, using the 2020 and 2021 observations.

## OD pairing, secondary
Cross-fitted estimator b of `PROTOCOL_OD_PAIRING_D2.md`, r25 and r10, on set A pooled over Monday and Saturday, with clusters by detector. Same classification and power rule. Not used to reclassify the primary result.

## Reading rule
No pass mark. Results are reported whatever they are; the set of validations in the paper is not chosen from them. Inclusion in the manuscript is the author's decision and must describe this comparison as supplementary, with the limits above.
