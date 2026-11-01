# Alpha plan

## Assessment of the existing platform (`platform/dashboard`)

| Component | Finding | Decision |
|---|---|---|
| Django 3.2 GUI | Server-rendered templates, one `Simulation` model with no failure state, 2021 pins, no real tests | Kept untouched, not used by the alpha |
| FastAPI 0.65 `sim-ws` | Hard-coded `$WORKSPACE/covid_hep` paths; `multiprocessing` without cancel, limits or recovery; imports the `pysim` binding; can delete outputs (`remove_local_output`) | Replaced by a new service, same framework family |
| Crono, nginx, compose | Tied to the former deployment (`.env.dev`, `work_lavoro`); not runnable here | Left in place |
| Engine (`minimocas/sim_engine`) | Independent executable: JSON in, files out, `.status` progress | Reused unchanged, called as a process |
| Science (`model/analysis`) | `demand_scaling.one` defines the frozen configuration | Reused by a bridge, not reimplemented |
| Security | Legacy login uses an env-provided password. No security audit or secret scan of the repository was done; the new app binds to localhost, see limitations |

The environment has no Docker. It has 4 cores, 13 GB RAM shared with research jobs, and a nearly full `/home`.

## Architecture decision

One FastAPI process with SQLite, a React frontend it serves itself, and a supervised subprocess per run.
Django is not needed: one user on one workstation needs no admin or user model yet. PostgreSQL/PostGIS, Celery and
Redis would add services with no current requirement: the network has 3,925 links and fits in one GeoJSON file.
Docker Compose is deferred, because it could not be tested here (see `BETA_ROADMAP.md`).

## Priorities

1. Reproducibility guard: the frozen configuration comes from the science code, verified against stored outputs.
2. Vertical slice: scenario → run → status → map and chart.
3. Failure handling: cancel, crash, exit 0 without output, timeout, restart.
4. Resource limits that protect research jobs on a shared machine.
5. A synthetic profile so the platform works without proprietary data.

## Acceptance criteria

The nine criteria of the brief; status and evidence in `ALPHA_TEST_REPORT.md`.
