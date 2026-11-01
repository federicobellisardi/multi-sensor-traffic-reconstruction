# Alpha progress

All items are done on branch `alpha/platform` unless marked otherwise.

- [x] Repository, engine contract and legacy platform inspected
- [x] Isolated worktree: the research checkout stays on `main`, with its uncommitted work untouched
- [x] Backend: scenarios, runs, job runner, results API, Alembic migration
- [x] Bridge to `demand_scaling`; frozen run byte-identical to the stored output
- [x] Synthetic demo profile on the public network
- [x] Frontend: map, runs, scenarios, comparison
- [x] Backend, frontend and browser end-to-end tests, also from a clean clone with a freshly built engine
- [x] Documentation
- [ ] Docker Compose: not provided, Docker is unavailable here
- [ ] Authentication: not implemented, localhost only

## Defects found by testing and fixed

- Demo departures rounded to zero at low demand, giving an empty simulation that looked deterministic.
- Switching a chart to its table showed nothing: ECharts `dispose` cleared the DOM node React had reused.
- A cancel arriving during the configuration step could be lost.
- Map clicks picked the first road in the hit box, not the road under the pointer.
- Repeated Y-axis tick labels at low flows.

## Findings about the research code (not changed)

See "Findings for the research project" in `docs/ALPHA_TEST_REPORT.md`.
