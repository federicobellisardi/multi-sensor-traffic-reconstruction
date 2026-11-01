#!/bin/bash
# One-time setup: build the simulator (minimocas) and create the Python environment.
# Needs cmake >= 3.11, a C++14 compiler, Boost (filesystem) and conda/mamba; run it on every OS you use
# (the build goes to $WORK_ROOT/build_<os>).   Usage: bash hpc/setup.sh
set -e
. "$(dirname "$0")/config.sh"
mkdir -p "$WORK_ROOT" "$LOGS"

cmake -S "$REPO/minimocas" -B "$BUILD"
cmake --build "$BUILD" --target sim_engine --parallel "${NPROC:-4}"
[ -x "$SIM_ENGINE" ] || { echo "simulator not built: $SIM_ENGINE"; exit 1; }

if [ ! -x "$PY" ]; then
  CONDA=$(command -v mamba || command -v conda || ls /common/conda/bin/conda 2>/dev/null | head -1)
  [ -n "$CONDA" ] || { echo "conda/mamba not found"; exit 1; }
  "$CONDA" env create -y -p "$ENV_DIR" -f "$REPO/environment.yml"
fi
"$PY" -c "import pandas, scipy, geopandas, contextily; print('python environment ok')"
echo "setup done: engine $SIM_ENGINE, python $PY, work root $WORK_ROOT"
