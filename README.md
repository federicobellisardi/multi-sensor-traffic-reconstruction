# Multi-sensor traffic reconstruction

Regional traffic simulation for Emilia-Romagna (Italy) from mobile-phone origin–destination
demand, an agent-based simulator on an OpenStreetMap-derived road graph, inductive loop detectors
(MTS) and GPS probes, with the analyses and manuscripts built on it.

## Contents

| Path | Content |
|---|---|
| `model/` | The regional model: analysis pipeline, aggregate results and manuscript (see `model/README.md`) |
| `digital_twin/` | Second paper: web platform for launching and inspecting simulations, and its analyses (see `digital_twin/README.md`) |
| `minimocas/` | Agent-based traffic simulator (C++, pybind11 interface) |
| `src/`, `CMakeLists.txt`, `cmake/`, `build.sh` | Build of the simulator and of the Python bindings |
| `vars/` | Project cartography (`vars/carto`, 3,925 polylines), simulator configurations and regional shapes; the metadata tables `vars/extra/*.csv` (detectors, no-turn rules, distances) are not tracked |
| `hpc/` | Setup, smoke test and job scripts for workstations and the Slurm cluster (see `hpc/README.md`) |
| `environment.yml` | Python environment of the analysis |
| `platform/` | Earlier operational platform, not used by the model pipeline: web dashboard (`dashboard/`), OD and configuration tools (`python/`), `scripts/` |
| `research/` | Literature, dataset provenance and processing scripts for companion studies |

The history of the previous manuscript revision is kept on the branch `revision-v2`.

## Build

```sh
bash hpc/setup.sh        # simulator (CMake, C++14 compiler, Boost filesystem) and Python environment
bash hpc/smoke_test.sh   # two simulated hours, about 30 s
```

The legacy `build.sh` builds the Python bindings (also needs pybind11). See `hpc/README.md` for the
location of working files and the cluster workflow.

## Data

Not included in this repository:

* TIM mobile-phone OD tables and Viasat GPS data: proprietary, not redistributable;
* MTS loop-detector counts: public (Regione Emilia-Romagna, CC BY), downloadable from the
  regional open-data catalogue (dataset DS-1944);
* ISTAT road-accident microdata: public, downloadable from istat.it (see
  `research/datasets/scripts/`);
* OpenStreetMap extracts: © OpenStreetMap contributors, ODbL (Geofabrik);
* the CSV tables in `vars/extra/`, `model/results/corrected/` and `model/results/road_class.csv`,
  which the pipeline reads at those paths (see `model/submission/REPRODUCIBILITY.md`).

Dashboard credentials are read from environment variables; see `platform/dashboard/.env.example`.

## Credits and licence

The reconstruction framework, the simulator `minimocas` and the web platform were developed in
the Physics of Complex Systems group of the University of Bologna (physycom) and at Mindicity.
This repository is distributed under the GNU GPL v3 (`LICENSE`). The licensing of `minimocas`
should be confirmed with its original authors before any public release.
