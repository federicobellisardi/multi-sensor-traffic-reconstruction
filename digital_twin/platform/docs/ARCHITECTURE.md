# Architecture

```
Browser (React, TypeScript, MapLibre, ECharts)
   │  HTTP/JSON, polling
FastAPI  digital_twin/platform/backend/app
   ├─ main.py      API; serves the built frontend
   ├─ profiles.py  validated parameters; what each profile can do
   ├─ jobs.py      queue, limits, supervision, recovery
   ├─ results.py   reads engine outputs (read only)
   ├─ network.py   display-simplified road network, cached
   └─ models.py    SQLite via SQLAlchemy, Alembic migrations
   │  subprocess, JSON file in, files out
   ├─ sim_engine              unchanged C++ executable
   └─ bridge/build_research_config.py    runs in the research Python environment,
                                         imports model/analysis/demand_scaling.py
```

**Separation.** The engine does not know about the platform. The platform knows only the engine's JSON input, exit
code, `.status` and `_uniq_` output. Scientific configuration lives in `model/analysis`; the bridge calls the same
functions as `demand_scaling.one`.

**Profiles.**
- `research_frozen`: frozen model configuration; optional overrides are a demand multiplier, seed and window, and any override clears the "Frozen model" label. Needs private inputs. Its data class is `proprietary-derived`.
- `demo_synthetic`: gravity-like invented demand between the nine provincial capitals on the real public network, dated 2000-01-03 so that it cannot be mistaken for a campaign day. Labelled SYNTHETIC in every view.

**Run lifecycle.** `queued → running → completed | failed`, and `cancelling → cancelled`. A run is complete only if the
engine exited with 0 *and* wrote the flow file, because the engine exits 0 on caught exceptions.

**Resource limits.** Concurrency 1, bounded queue, `nice 19`, `RLIMIT_AS`, a timeout, 2 OpenMP threads, and admission gates
on available memory and free disk. All are configurable (`ALPHA_*`).

**Traceability.** Each run directory holds the exact engine JSON and `manifest.json`: parameters, seed, SHA-256 of
configuration (without the output path), engine and output, and the git commit with a `-dirty` suffix if `minimocas`,
`model/analysis` or `vars` have uncommitted changes in the science checkout. Parameters are a snapshot: editing a scenario does not alter past runs.

**Data boundaries.** State lives in `$ALPHA_STATE_DIR`, outside the research outputs. Finished research runs under
`$SIM_RUNS/demand/{V6_scaled,V0_scaled}` are registered read only, without copying. Link-level results of proprietary origin must stay out of git; committed screenshots come only from the synthetic profile.

**Extension point.** `perturbations` is a discriminated union with one kind, `demand_scale`. `road_closure` is rejected with HTTP 422 and reported as unsupported until the engine and tests support it.

**Choices that can be revisited.** SQLite uses a rollback journal because the state may be on NFS. Polling instead of
WebSockets. One server process: the job runner lives inside it, so stopping the server stops active runs and records them as interrupted.
