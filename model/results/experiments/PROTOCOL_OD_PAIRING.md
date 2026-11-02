# Value of OD pairings with marginals preserved: protocol

Written on 2026-11-01. Frozen model unchanged. All data have been seen, so every result is exploratory.

## Question
Given how many trips leave and enter each place in each interval, does knowing who goes where improve the reconstruction?
The existing removal of relations does not answer this: it also removes the marginals by municipality.

## Decisions before the runs (user, 2026-11-01)
Destination code 000000000 (column 000000000000, name N/A, 30-32% of inter-municipal trips) is removed from the demand of all arms, and the
remaining agents are multiplied so that the total is unchanged (the `_x` configurations). The frozen model is not changed by this.
Endpoint radius of 5 km: not included. On the calibration half without factors it does not improve dispersion or ranking clearly, and the volume ratio falls
(N50 0.97, N100 0.86, N347 0.62, code removed), so the criterion "include if it improves" is not met.
Direct validation against Viasat trips: not possible, the raw traces are no longer available; the link tables have no origin or destination.

## Arms (Monday and Saturday, k, factors, routing and random-end classes as the frozen model)
Coverage: N50_r20_x and N347_r20_x. Real, null D, null M. Three permutations per null, coverage and day; real with engine seeds 1 and 2.
Null M: within each 15-min interval, destinations of municipal relation agents are permuted among them. O_i(t), D_j(t) and the total are exact.
Null D: swaps accepted only if each agent stays in the distance bin of its real pair (0-5, 5-10, 10-20, 20-50, >50 km) and has no self-pair.
Province relations and random-end classes are unchanged. The permutation follows the factors. 32 simulations.
Level is not retuned: comparisons are within a coverage, with the same agents.

## Checks before evaluation
Marginals by interval identical to the real arm. Distance by bin: null D equal to real, null M different. Share of agents moved to another destination.

## Power, decided first
Sensitivity: median |log10(real/null)| of daily volume at detectors and on all links.
Twin test: real seed 1 as synthetic truth at the detectors of each set. Can dispersion and Spearman separate real seed 2 from each null?
If not, null results on these detectors are reported as not determined.

## Validation
Primary: dispersion and Spearman, test half and 2021, four comparisons, real minus mean of the permutations; paired bootstrap over detectors, 2,000 resamples.
Secondary: Spearman with GPS link counts, Forli-Cesena and elsewhere; the quartile of detectors most sensitive to the permutation (from real against null M, without observations).

## Deviation after the runs, before evaluation
The six N347 null M runs (about 89,000 sources) ended with a segmentation fault after about 2 minutes, within the memory limit; cause not confirmed. The simulator was not changed and the null was not redefined. Null D is complete; null M exists only for N50, so at N347 the sensitive quartile and the sensitivity use null D.

## Rules
Pairing supported if, in C347 or C50, real beats null D: Spearman interval above zero or dispersion interval below zero, in at least two of four comparisons, on the same metric.
Real beats null M but not null D: value in the distance structure only, not in specific pairs.
No difference with adequate twin power: no measurable value in link counts. No difference without power: not determined.
