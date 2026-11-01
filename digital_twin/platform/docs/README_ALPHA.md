# Regional mobility platform: alpha

A research alpha for launching and inspecting traffic simulations of Emilia-Romagna.
**It is not a validated predictive digital twin.** It shows raw simulator link flows, before detector correction.

## Requirements

Linux, `uv`, CMake ≥ 3.11, a C++14 compiler, Boost `filesystem`, and Node ≥ 20 (or conda/mamba, which setup then uses to install it). Browser tests need Chrome (`CHROME_PATH`, default `/usr/bin/google-chrome`).

## Install and start (no private data needed)

From the repository root:

```sh
export WORK_ROOT=$PWD/.work                     # any disk with about 2 GB free
. hpc/config.sh
cmake -S minimocas -B "$BUILD" && cmake --build "$BUILD" --target sim_engine --parallel 4
bash digital_twin/platform/scripts/setup.sh
bash digital_twin/platform/scripts/run.sh
```

Open <http://127.0.0.1:8765>; API documentation is at `/docs`. `hpc/setup.sh` also builds the engine, but creates the full research environment too.

First run: **Scenarios → Demo baseline (SYNTHETIC) → Launch**, then **View on map** when it completes.

## With the private research inputs

The frozen profile enables itself when its inputs exist (see `hpc/README.md`). The Scenarios page reports what is missing. Settings go in `digital_twin/platform/.env` (see `.env.example`):

```sh
SIM_ENGINE=/path/to/current/sim_engine      # check that the app shows no engine warning
ALPHA_SCIENCE_ROOT=/path/to/research/checkout   # if this checkout has no private inputs
```

## Tests

```sh
bash digital_twin/platform/scripts/test.sh    # backend, frontend, browser end-to-end with the real engine
```

The browser suite rewrites `digital_twin/platform/docs/screenshots/` using synthetic data only.

## Data handling

The server has **no authentication** and binds to `127.0.0.1`. Do not expose it: research runs contain link-level data derived from proprietary sources. Never commit their results or screenshots.
