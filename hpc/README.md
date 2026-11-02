# Running the simulations and the analysis (workstation or cluster)

Everything is driven by the repository location; no fixed paths. Settings are in `config.sh`
and can be overridden in the environment or in `hpc/local.sh` (git-ignored; copy `local.sh.example`).

| Variable | Meaning | Default |
|---|---|---|
| `WORK_ROOT` | large files outside the repository: Python environment, builds, simulation outputs, logs (`MOVER` is accepted as the former name) | `<repo>/.work` |
| `SIM_RUNS` | simulation outputs and route-choice inputs (`routing/`, `coils/`, `demand/`) | `$WORK_ROOT/sim_runs_nocode2` |
| `SIM_ENGINE` | `sim_engine` executable | `$WORK_ROOT/build_<os>/sim_engine` |
| `RESULTS_DIR` | aggregate results of the analysis | `<repo>/model/results` |
| `DATA_CACHE` | downloaded public data (MTS monthly tables, OSM extract) | `<repo>/data/cache` |

## Steps

1. **Setup** (once per OS/machine; needs CMake ≥ 3.11, a C++14 compiler, Boost with `filesystem`, conda or mamba):
   `bash hpc/setup.sh` builds the simulator into `$WORK_ROOT/build_<os>` (one build per OS release, so a
   workstation and a cluster sharing the same disk do not overwrite each other) and creates the
   environment from `environment.yml`.
2. **Private inputs** (never in git): the coil tables under `data/`, the Viasat link-speed tables under
   `work_viasat/`, `model/results/private/` (git-ignored; may be a symlink), the OD configurations
   `article/python/revision/rerun/work/conf_nocode/*.json`, and the route-choice and coil inputs in
   `$SIM_RUNS/{routing,coils}`.
3. **Smoke test**: `bash hpc/smoke_test.sh` simulates two hours of 10 February 2020 (about 30 s) and checks the
   output.
4. **Everything, in order** (IFISC cluster, Slurm wrapper `run`): `bash hpc/run_all.sh` builds the demand, chooses radius and `k`, tests the departure shift, sets and evaluates the province factors, runs the final simulations and experiments, and submits `hpc/pipeline.sh`. One script: `bash hpc/run_script.sh demand_scaling.py one V6_scaled 2020-02-10`. Unfinished simulations of one script: `bash hpc/submit_stage.sh SCRIPT [TIME] [MEM]`.

The final configuration is set in `config.sh`.
