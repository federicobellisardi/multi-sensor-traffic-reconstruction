# How minimocas behaves, as configured in model v2

Written 2026-11-02. Each item says how it is known: **read** (code), **measured** (outputs of model v2, Monday), **not tested**.

## Trips
- **Known pairs are not pinned (read).** A source with a location has its destination redrawn among nodes within the radius (`cherry_pick`, 25 km), weighted by population. With `spread_origin` the origin is redrawn around the source too (`make_pawns`, `simulation.cpp:1446-1505`).
- **Trip length of known pairs (measured).** About 27 km per agent (`scr_dest`, 12.7 million km for 464,428 agents; N347 27 km), against 12-13 km between the centres of the same pairs. Probably due to the redrawing; path detours were not separated.
- **Random-end agents ignore their known end while moving (read).** `beta_bp_miss` is 1.0 for `rnd_dest`, `src_rnd` and `rnd_rnd`, so `pick_next_bp` always takes the transition branch. The known end sets only where the agent starts. They walk until `TTB`, drawn uniformly in 900-5,600 s, or until they happen to reach `current_dest`.
- **Length of random-end trips (measured).** 42-45 km per agent, and 79-80% of agent-km in the reported model. At N347 they are 8%.
- **Agent-km come from hourly snapshots** of `_pawn_` files (snapshots x 3,600 s x mean speed): an estimate, not a trip log.

## Routes
- **One route (read).** `next_hop` gives one next node for each type, destination and node. `beta_bp_miss` is 0 for `scr_dest`, so all its agents with the same type and destination share the tree of best paths.
- **Static weights (read).** `dynamic_weights` is not in our configuration. `get_weight` uses length, speed and class usage.
- **Agent types are arbitrary (read and run).** Each key under `pawns` gets its own weights and matrix.
- **Transition weights (read).** `make_tmatrix` uses `cntFT`/`cntTF` (`file_cnt`, by class in V6). Choice does not depend on destination.

## Speed and congestion
- **Practically no congestion (read).** `density_critical` is 3/4.20 agents per metre, about 714 per km, per link and for both directions together; `speed_t` falls linearly from the free speed to 10 km/h. Mean speed is about 16 m/s, 58 km/h (measured).
- **Consequence (not tested).** Feeding simulated speeds back into routes would change little. A route step responding to traffic needs its own volume-delay function.

## Counts
- **Link flows (read).** `uniq` counts distinct agents per hour and direction, sampled at each step. Direction comes from the sign of `pawn.speed`.
- **Detector counts (read).** `update barriers` uses crossings in `evolve`. Some conditions look odd (`p.current_s - ds < 0.0`), and an agent changing link within a step may be missed. Not tested; the paper notes virtual counters about 8% below distinct-agent counts.

## Random numbers
- **Two or more generators (read).** `pawn.h` has `static std::mt19937 generator`, so each source file has its own copy. `simulation.cpp:752` seeds only its own, so draws in `pawn.cpp` (transition choice, leaving the best path) do not follow the seed.

## Defects
- **`dump_sources` (read and reproduced).** It indexes `c->node[s.node_lid]`, and `node_lid` is uninitialised for sources with no `source_location` (`_dest_OUT`, `LOCALS`). Results are garbage rows in `_sources.csv`, or a segmentation fault that depends on memory. Corrected on branch `explore/od-routing` by skipping those rows. The frozen binary of model v2 still has it.
- **Probably the same defect (not tested):** the fault of null M at 347 municipalities, and the "long paths" crash of LOCALS-only runs, which led to the `nr_*` directories.
- `pawn.flow` holds near-zero garbage in `_pawn_` files (measured, unused by the analysis).

## Not read in depth
`make_pawns_weight`, attractions, transports, `dynamic_weights` modes, map-matching and `carto_edit.cpp`.
