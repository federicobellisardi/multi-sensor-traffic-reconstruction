# Implementation and evidence audit — 2026-10-27

## Primary archive assessment

`analysis/validate_archive.py` independently reproduces link MAE, raw MAE,
OD-baseline MAE, Pearson correlation and model-relative GPS ratio from the
archived simulations and original local GPS extracts. It asserts agreement with
the existing metrics within 1e-9 and identical usable-link sets. The original
analysis directories are not output destinations.

The revised 2021 MTS comparator preserves all-missing hourly cells as missing,
instead of converting them into zeros. It uses 456–470 complete direction
profiles per date rather than treating 471 as uniformly usable. Median MAE
changes from 1.2142652294 to 1.2155632572 pp; the baseline still beats the model.
The original comparator is recorded as provenance, not silently overwritten.

## Historic count-validation limitations

The archived LOO table has 610 coil-days and 1,202 directional records: 18 fewer
than two directions per coil-day. Its runner skips a direction when the corrected
output does not contain 24 values. This needs reconciliation before a final
count-validation claim. Complete raw counter input does not guarantee complete
corrected output.

The new pilot exposed a concrete example: polyline 260156 has node 262686 as a
degree-one endpoint and 4,273 raw simulated counts in direction TF on 10 February
2020. Withholding its coil can remove that direction from the correction output.
The forward-weight-based initialization does not retain every raw directed link;
direct coil updates can create entries that are absent when the coil is withheld.
The pilot therefore excludes terminal-link coils before splitting and refuses
to silently omit missing test keys. Its restricted sample cannot repair or
replace the full historical LOO assessment.

Other inherited defects remain: UTC observations treated as local in archived
assimilation; early and incomplete hourly demand mapping; sibling turning weights
compounded; shared visited-link budget; unique-link occupancy versus point counts.
The post-correction need not conserve flows at nodes.

## One-day replay

The archived 10 February 2020 configuration was replayed through the existing
Python 3.12 `pysim` wrapper and reconstructed historic workspace. The process
finished in 607 s with the same directed-link keys and hourly labels, but
**did not reproduce the historical numeric result**.

- Archived sum of link-hour counts: 34,334,965.
- Replay sum: 33,361,561. These sums are traversal/occupancy counts, not trips.
- Mean absolute cell difference: 43.2983 counts; maximum: 71,547.
- 88.80% of cells differ.

`results/replay_20200210.json` records input and binary digests. The simulator's
hard-coded seed does not explain or rule out software-version, graph, metadata
or input differences. No cause has yet been established. Do not promote a
corrected-demand comparison against the archived outputs until the replay
difference has been isolated. Compare candidate variants within a verified
common environment and retain the historical assessment separately.

## Reproduction and next fix

```sh
python3 article1/analysis/replay_day.py          # compare existing local replay
python3 article1/analysis/sensor_sensitivity.py # one-day pilot, may take minutes
```

Before further full-campaign LOO: preserve every raw directed key in a corrected
implementation, define multiedge and terminal-link behaviour, score against
local-time counts, and report every exclusion. Compare the corrected algorithm
with a faithfully reproduced historic algorithm; do not silently change their
definitions. Add targeted conservation/branch tests where the intended semantics
are explicit. No edits to simulator or original assimilation code were made.
