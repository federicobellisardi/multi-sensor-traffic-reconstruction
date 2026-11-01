# Shared settings of the scripts in hpc/ (source it; nothing is executed).
# Everything is derived from the repository location; override any variable in the environment or in
# hpc/local.sh (git-ignored, see local.sh.example).
HPC_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO=$(dirname "$HPC_DIR")
[ -f "$HPC_DIR/local.sh" ] && . "$HPC_DIR/local.sh"

# WORK_ROOT: large files that do not belong in the repository (environment, builds, simulation
# outputs, logs). MOVER is accepted as the previous name of the same variable.
WORK_ROOT=${WORK_ROOT:-${MOVER:-$REPO/.work}}
OS_TAG=$(. /etc/os-release; echo "$ID$VERSION_ID")   # binaries depend on the local glibc/libstdc++
BUILD=${BUILD:-$WORK_ROOT/build_$OS_TAG}
ENV_DIR=${ENV_DIR:-$WORK_ROOT/env}
LOGS=${LOGS:-$WORK_ROOT/logs}

export SIM_RUNS=${SIM_RUNS:-$WORK_ROOT/sim_runs}
export SIM_ENGINE=${SIM_ENGINE:-$BUILD/sim_engine}
PY=${PY:-$ENV_DIR/bin/python}
[ -f "$WORK_ROOT/carto_key" ] && export CARTO_API_KEY=$(cat "$WORK_ROOT/carto_key")
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-2}
