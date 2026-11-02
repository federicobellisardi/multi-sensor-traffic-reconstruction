# Better routing for origin-destination pairs: design and protocol

Registered on 2026-11-02, before the runs of step 1. Branch `explore/od-routing`. The paper on model v2 stays at the branch `submission/epj-data-science` and nothing here changes it.

## Why
The author wants a more precise model that uses the origin-destination pairs. Targets: higher GEH, and an hourly error at held-out detectors below 10%, with 20-25% already acceptable. Today it is about 40%, and about two thirds of it on weekdays is level at the single road.

## Hypothesis
With almost all demand on specific pairs (N347), many roads lose their traffic because all agents of a pair and type follow one fixed best path. Spreading a pair over several routes should restore those roads while keeping the ranking.

Alternatives: the endpoints of trips, the intra-municipal trips left out, or the partial network cause the loss. This has not been tested, and detector data have been seen.

## Detector split
- **Blind:** half of the 97 test detectors, drawn by province with seed 20261103. Not used in any step, and opened once at the end of the whole work. Their 2021 rows are also excluded.
- **Development:** the 100 calibration detectors and the other half of the test detectors, in 2020 and 2021.

The blind set is not truly unseen, because it entered earlier versions of the model. Stated limit.

## Step 1: arms
All at N347, 25 km, the factors and `k` of v2 with no retuning, Monday and Saturday; engine unchanged.

| Arm | Change for located pairs (`scr_dest`) |
|---|---|
| `real` | none: existing run `od_pairing/N347_real_s1` |
| `multi4` | each pair split equally over four agent types: (alpha, alpha_s) = (1, 0), (0, 1), (0.25, 0), (0.5, 0.25) |
| `miss10` | `beta_bp_miss` 0.10: at each node an agent leaves the best path with this probability |
| `miss30` | `beta_bp_miss` 0.30 |
| `multi4_miss10` | both |
| `multi4_s2` | `multi4` with seed 2, for the variation between runs |

These values are choices, not estimates. The reported model on the same detectors is the reference.

## Metrics
On development detectors, per day and year. `k` is not retuned, so the main metric removes the level of the arm:
- **Low tail (primary):** share of detectors more than a factor of 2 below, after subtracting the median log10 ratio of the arm.
- Spearman, robust spread, dispersion, median absolute log10 ratio, volume ratio, with 95% paired bootstrap against `real`.

## Decision rule for step 1
Mean low tail over the Monday and Saturday of 2020:
- **Success:** at most 10% with a mean Spearman no more than 0.02 below `real`. Go to step 2.
- **Failure:** above 20%. Routing is not the main cause: stop, and report before touching the engine.
- **Between:** report and decide with the author.

One arm is chosen among several, so a success is exploratory.

## Later steps, only after step 1
2. Routes that respond to traffic: repeat runs, updating the weights from flows.
3. Adjust the OD matrix with counts on development detectors.
4. Link weights and correction.
5. Open the blind set once; report hourly error and GEH.

Any new model must then repeat the selection and all tests of the paper. Omitted from this step: GEH and hourly error, which come after a route model is chosen.

## Known limits
- `minimocas/src/lib/pawn.h` has a `static` generator in a header, so each source file has its own copy and `simulation.cpp` seeds only its own. The draws in `pawn.cpp` (leaving the best path, random walks) do not follow the seed. `multi4_s2` therefore understates the variation between runs.
- One simulated day per day type.
