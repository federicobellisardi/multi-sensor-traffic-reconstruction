# Value of OD pairings, null D2: amendment 1

Registered on 2026-11-02, after Phase 0 failed and before any D2 simulation was run. It amends `PROTOCOL_OD_PAIRING_D2.md` (sha256 563e7f088dac3f1a96d1af6f55590479c8695af481b9f20a6956f8548b891e28), which stays unchanged. Approved by the author.

## What happened
With 2 km bins, G1 passed but G2 failed: 34% of agents moved, against the required 50%, in all reps and on both days (`od_pairing_d2_check_2km.json`). The share saturates near 0.32 in a peak interval as sweeps grow, so more sweeps cannot reach the threshold.

## Change
The distance bins of D2 become 4 km (0-4, ..., 96-100, >100 km). Nothing else changes: thresholds, gates, arms, seeds, estimator, classification and runs are as registered.
G1 and G2 are repeated with the new bins before the simulations, and G1 now requires an identical histogram in 4 km bins. A failure stops the simulations.

## How the width was chosen
Share moved, daily mean gap and KS distance on the 2 km distribution were measured for widths 2, 3, 4, 5, 7 and 10 km on the generator only. No D2 run existed, and no detector was compared with any D2 arm. 4 km is the narrowest width that reaches 50%: 51.5% on Monday and 51.7% on Saturday, mean gap 0.25%, KS 0.004-0.005.

## Limits
The width was chosen after the share moved was seen, and it clears the threshold narrowly.
A wider bin controls distance less tightly than the registered one. Within a bin, trip length can differ by up to 4 km, so a detected effect could include a small distance component; the mean-gap and KS figures above bound it at the level of the distribution, not of the single trip.
The synthetic controls E1-E3 depend on the template of the old runs, not on the bin width, and are not repeated. Measured power comes from the new runs, as registered.
