# Paper 2 — literature positioning (working notes, 2026-10-27)

Working title: "Dynamic traffic exposure reveals temporal patterns of road accident risk".

## Established knowledge (do not claim as new)
- Exposure is a denominator concept with competing measures (vehicle-km, time, counts)
  [wolfe1982, chipman1992, qin2004]; choice of measure changes rate rankings.
- Crash–flow relations at hourly resolution are nonlinear, often U-shaped in crash *rate*
  [ceder1982a/b, martin2002, lord2005flow, golob2004, dickerson2000]. A sub-linear
  hourly exponent (alpha < 1) is therefore expected, not a new scaling law.
- Night-time excess risk has known contributors: darkness [sullivan2002], alcohol [keall2005],
  driver mix [massie1995], speed [elvik2013power]; weather [bergel2013, theofilatos2014].
- Count models: Poisson / NB, overdispersion, low-mean issues [lord2005models, lord2006lowmean,
  mitra2007, lord2010, mannering2014, cameron2013, hauer2015].
- Aggregation / ecological inference: MAUP [fotheringham1991], ecological fallacy [robinson1950],
  aggregated vs disaggregated NB [lord2009aggregation].
- Measurement error in exposure biases SPF coefficients [elbasyouny2010] — direct anchor for the
  uncertainty-propagation contribution.
- Real-time crash-risk from loop detectors exists for motorways [abdelaty2004]; our setting is
  regional extra-urban roads with aggregate accident records, not crash-precursor detection.

## Candidate contribution (to be tested)
Using record-level ISTAT microdata 2022–2024 (hour × weekday × quarter × road type × province)
and *observed* MTS counts from the same years, compare inferences from (i) raw counts,
(ii) static exposure, (iii) observed dynamic exposure, (iv) simulated exposure; quantify how
exposure uncertainty (station sampling, day-to-day variability, model–observation discrepancy)
propagates into hourly relative risk and the accident–exposure exponent; test the exponent's
dependence on aggregation. Spatial claims limited to province / road-category level, plus a
road-level analysis for 2017–2018 (ISTAT road number + km) matched to MTS stations.

## Gaps still to search
Italian/European studies using regional loop-detector counts as exposure for time-of-day risk;
studies propagating exposure uncertainty into time-of-day risk; COVID-era mobility rebound in Italy.
