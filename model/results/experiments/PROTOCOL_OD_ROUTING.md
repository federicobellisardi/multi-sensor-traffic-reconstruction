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

## Amendment 1, 2026-11-02, before any result of step 1 was evaluated
**Engine.** The arms `multi4*` ended with a segmentation fault in `dump_sources`, which indexes an uninitialised `node_lid`. This step therefore deviates from "engine unchanged": the arms `multi4*` run with a binary in `$WORK_ROOT/build_explore`, whose only change skips sources without a location in that diagnostic file, and only if it reproduces the v2 Monday link flows byte for byte. The arms `miss*` ran with the earlier binary. Their source is the same.

**Added comparison, descriptive, outside the decision rule.** The run `od_pairing_d2/r10_real_s1` (N347, endpoints within 10 km) is reported with the same metrics. Reading the engine showed that known pairs have both ends redrawn within 25 km, and travel about 27 km against 12-13 km between centres, so this redrawing is an alternative explanation for the loss of roads (`model/notes/ENGINE_NOTES.md`).

## Step 1 outcome and amendment 2, 2026-11-02
Step 1 fell between the thresholds: best low tail 11.9% (`miss30`), against 17.9% for `real` and 6.5% for the reported model. With the author, routing is not pursued further for now.

## Step 1b: trip length, registered before its runs
**Observation (exploratory, TIM OD, Monday).** Inter-municipal trips have a mean centre-to-centre distance of 12.0 km, with 96.5% below 25 km. The reported model simulates about 40 km per agent (random-end agents 42-45 km, known pairs 27 km), so about 2.5 times the OD distance even with an assumed 30% detour.

**Hypothesis.** `k` and trip length compensate each other: long walks reach the right level with too few agents, and spread traffic over the network. Shorter trips with a higher `k` should lower dispersion. Alternative: the long walks compensate something else, such as missing short or long trips in the tables.

**Arms.** Model of v2 (50 municipalities, v2 province factors, not re-estimated), engine in `$WORK_ROOT/build_explore`, Monday and Saturday:
- `TTB` 900 s for random-end agents (the minimum the engine allows: fixed walk of about 14 km), radius of known pairs 25 km or 10 km, `k` 2.0, 2.5, 3.0, 3.5, 4.0, 5.0.
- `TTB` 1,800 s (900-1,800 s), radius 25 km, `k` 2.0, 2.5, 3.0.

Known pairs use the 10-km radius only where both ends have at least 3 nodes within it, as in `od_matrix.py`.

**Selection.** For each day and configuration, `k` minimises the mean squared log10(sim/obs) on the calibration half. The test half of development and the 2021 development detectors are used only to evaluate. The blind 49 detectors stay out.

**Decision rule.** On the development test half, mean of Monday and Saturday, against the reported model on the same detectors:
- **Holds:** dispersion below that of the reported model, with volume ratio within 0.90-1.10 and a selected `k` not at the edge of the grid.
- **Does not hold:** dispersion equal or higher, or `k` at the edge. Then the reported model stays the base.

Dispersion also gets a 95% paired bootstrap interval, and 2021 is reported beside it. Hourly error and GEH are not computed in this step. One configuration is chosen among several, so a success is exploratory.

## Step 1b outcome and step 1c, last test of this line, registered before its runs (2026-11-02)
Step 1b did not hold: dispersion on the development test half 0.27-0.30 against 0.22, with higher Spearman (0.75-0.76 against 0.72). The province factors had been kept from v2, which may penalise the arms.

**Arm.** `TTB` 1,800 s, radius 25 km. As in v2, `k` is chosen first without factors, on the calibration half, per day type, on the grid 1.5, 2.0, 2.5, 3.0, 3.5. Then two rounds of factors on the calibration half, with the rule of `province_demand.py` (median by province over both day types, clipped to 0.5-2.5), and `k` fixed.

**Decision rule, as in step 1b.** On the development test half, mean of Monday and Saturday, against the reported model: holds if dispersion is below it, the volume ratio is within 0.90-1.10 and `k` is not at the edge of the grid. If it does not hold, this line stops and the reported model stays. 2021 is reported beside it, including its volume ratio. The blind detectors stay out. If it holds, hourly error and GEH are computed next, and any adoption means repeating the selection and all tests of the paper.

## Step 1c outcome and end of this line, 2026-11-02
Step 1c did not hold: dispersion on the development test half 0.272 against 0.222, volume ratio 1.05, `k` 2.5 on both day types and not at the edge of the grid. Spearman 0.734 against 0.721 there, and 0.663 against 0.621 in 2021, both exploratory and with intervals that include zero. By the registered rule this line stops and the reported model stays. Later steps were not run, and the blind detectors were not opened.
