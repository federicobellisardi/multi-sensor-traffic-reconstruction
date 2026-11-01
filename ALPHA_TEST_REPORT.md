# Alpha test report

Date: 2026-11-01. Host: Ubuntu 26.04, 4 cores, 13 GB RAM, Chrome headless with software WebGL. Commits are on branch `alpha/platform`.

## Acceptance criteria

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Reproducible start with documented commands | Met, without Docker | Clean clone: engine build, `setup.sh`, `run.sh` |
| 2 | Dashboard displays a real road network | Met | E2E test 1: more than 1,000 rendered road features; real public cartography |
| 3 | Create and launch with the real engine | Met | E2E test 4 |
| 4 | Status, completion, errors, cancellation | Met | E2E tests 4, 5, 6; backend tests |
| 5 | Results on maps and charts | Met | E2E test 4: table values equal the engine's CSV |
| 6 | Previous runs stay accessible | Met | E2E test 7: real server restart |
| 7 | Core tests pass | Met | Below |
| 8 | Scientific workflow stays functional | Met for what was run | Smoke test; byte-identical frozen run; the pipeline itself was not re-run |
| 9 | Another developer can reproduce it | Partly met | Verified by a clean clone on this machine with the same tools; not tested on another machine or by another person. Frozen profile needs private inputs |

## Commands and results

| Command | Where | Result |
|---|---|---|
| `bash platform/alpha/scripts/test.sh` | Clean clone, freshly built engine, no private data | 25 backend, 11 frontend, 8 browser tests passed |
| `SIM_ENGINE=…/build_ubuntu22.04/sim_engine bash hpc/smoke_test.sh` | Research checkout | Passed: 7,850 rows, 34 s; `git status` unchanged |
| `bash platform/alpha/scripts/run.sh` | Worktree, private inputs available | Started, 30 research runs imported, frozen profile available, no engine warning |

Backend tests mostly use a stand-in engine to force failures. `test_engine.py` and all browser tests use the real one, with no mocks.

## Scientific integrity checks

| Check | Result |
|---|---|
| Frozen run (Monday 10 Feb 2020, V6) launched through the API, against `sim_runs/demand/V6_scaled` | `_uniq_` and `_barriers_` files byte-identical (SHA-256 `3b7f33cf…`, `0fdf0210…`); configuration differs only in `state_basename` |
| Same run limited to 6 hours, against the first 6 bins of the full run | 0 of 47,100 cells differ, so truncating the window does not alter the earlier bins |
| Same synthetic configuration and seed, run twice | Byte-identical |
| Different seed | Different output |
| Freshly built engine against `build_ubuntu22.04`, two synthetic configurations | Identical hashes. Only these short runs were compared, not a full research day |
| Files of imported runs after reading | Unchanged, by test on a synthetic fixture |

Only one frozen day was regenerated. The frozen run and the 6-hour run are the only tests with proprietary-derived data; their outputs are not committed.

## Known limitations

- Not validated: no comparison with detectors or GPS in the platform, and no uncertainty on comparisons.
- Flows are raw: the detector-corrected outputs (`.csv.corrected`) are not exposed, so these numbers are not the reconstruction reported in the manuscript.
- The 23:00 bin of frozen runs covers 45 minutes. The app states this.
- Only a uniform demand multiplier is available. Road closures are not. Multipliers other than 1 have run only on synthetic demand.
- No authentication; one server process; stopping it interrupts active runs (recorded as failed).
- Docker Compose, PostgreSQL/PostGIS and Django are not used. Compose was not delivered because it could not be tested.
- The memory limit was set but not exercised by a run reaching it. The admission gates and timeout are tested.
- Real-data browser use was exercised by one ad-hoc session (map colouring and road selection), not by the automated suite, which is synthetic by design.
- Dark mode is implemented but was not inspected; all screenshots are in light mode.
- The JavaScript bundle is 1.46 MB (436 kB compressed).

## Findings for the research project (nothing changed)

1. **Stale default engine.** On this machine `hpc/config.sh` resolves to `build_ubuntu26.04/sim_engine` (29 Oct), which has no seed option. On one synthetic configuration it counted 4,108 link passages against 17,709 for `build_ubuntu22.04`. Research jobs set `SIM_ENGINE` explicitly, but any script relying on the default uses the old binary. The platform warns about such builds.
2. **Partial seeding.** `minimocas/src/lib/pawn.h:31` declares `static std::mt19937 generator` in a header, so each translation unit has its own copy. Only the copy in `simulation.cpp` is seeded (line 752); the draws in `pawn.cpp` (lines 104, 144) always use the default state. Seeds do change results, but seed-to-seed spread may understate stochastic variability. This comes from reading the code; the effect has not been measured.
3. **Smoke test differs from the frozen model.** `hpc/smoke_test.sh` omits `province_scaled` and uses `k` for every day, so passing it does not exercise the frozen demand.

## Screenshots

Synthetic data only, in `platform/alpha/docs/screenshots/`: empty network, monitoring, completed run, map with road chart, comparison, failed run, phone layout.
