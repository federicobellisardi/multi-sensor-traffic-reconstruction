#!/bin/bash
# One-time setup on the IFISC cluster (nuredduna): build minimocas and create the Python environment.
# Run from the repository clone, which must be named covid_hep (the correction reads ../covid_hep/vars):
#   cd /data/workspaces/fbellisardi/mover_data/covid_hep && bash article1/cluster/setup.sh
set -e
REPO=$(cd "$(dirname "$0")/../.." && pwd)
MOVER=${MOVER:-$(dirname "$REPO")}
[ "$(basename "$REPO")" = covid_hep ] || { echo "the clone must be named covid_hep"; exit 1; }

# simulator (Release build; Boost from the system)
cmake -S "$REPO/minimocas" -B "$MOVER/build_minimocas" -DCMAKE_BUILD_TYPE=Release
cmake --build "$MOVER/build_minimocas" --target sim_engine --parallel 4
mkdir -p "$REPO/minimocas/bin"
ln -sf "$MOVER/build_minimocas/sim_engine" "$REPO/minimocas/bin/sim_engine"

# Python environment for the analysis
if [ ! -x "$MOVER/env/bin/python" ]; then
  /common/conda/bin/conda create -y -p "$MOVER/env" -c conda-forge \
    python=3.12 pandas numpy scipy matplotlib geopandas shapely pyproj contextily
fi
"$MOVER/env/bin/python" -c "import pandas, scipy, geopandas, contextily; print('python environment ok')"
echo "setup done"
