# Multi-sensor traffic reconstruction

Regional traffic reconstruction for Emilia-Romagna (Italy) from mobile-phone origin–destination
demand, an agent-based simulator on an OpenStreetMap-derived road graph, inductive loop detectors
(MTS) and GPS probes, with the analyses and manuscripts built on it.

## Contents

| Path | Content |
|---|---|
| `minimocas/` | Agent-based traffic simulator (C++, pybind11 interface) |
| `src/`, `CMakeLists.txt`, `cmake/`, `build.sh` | Build of the simulator and of the Python bindings |
| `python/` | OD processing, simulation configuration and analysis tools |
| `vars/` | Project cartography (`vars/carto`, 3,925 polylines) and metadata (detectors, no-turn rules) |
| `dashboard/` | Web platform: FastAPI simulation service, Django dashboard, MTS data fetcher, nginx |
| `article1/` | Article 1, *Large-scale traffic flow reconstruction from heterogeneous mobility sensors*: manuscript, supplement, analysis pipeline (`article1/analysis`) |
| `research/` | Programme notes, literature, dataset provenance and processing scripts for the companion studies |

The history of the previous manuscript revision is kept on the branch `revision-v2`.

## Build

```sh
./build.sh          # requires CMake, Boost and pybind11
```

## Data

Not included in this repository:

* TIM mobile-phone OD tables and Viasat GPS data: proprietary, not redistributable;
* MTS loop-detector counts: public (Regione Emilia-Romagna, CC BY), downloadable from the
  regional open-data catalogue (dataset DS-1944);
* ISTAT road-accident microdata: public, downloadable from istat.it (see
  `research/datasets/scripts/`);
* OpenStreetMap extracts: © OpenStreetMap contributors, ODbL (Geofabrik).

Dashboard credentials are read from environment variables; see `dashboard/.env.example`.

## Credits and licence

The reconstruction framework, the simulator `minimocas` and the web platform were developed in
the Physics of Complex Systems group of the University of Bologna (physycom) and at Mindicity.
This repository is distributed under the GNU GPL v3 (`LICENSE`). The licensing of `minimocas`
should be confirmed with its original authors before any public release.
