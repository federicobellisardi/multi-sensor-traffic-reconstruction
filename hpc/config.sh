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

export SIM_RUNS=${SIM_RUNS:-$WORK_ROOT/sim_runs_v2}   # runs of model v2; the links in it point to shared inputs in $WORK_ROOT/sim_runs (model v1: tag frozen-v1, sim_runs_nocode2)
# The results come from this binary, on every machine; a build for the local OS is used only if it does not exist.
FROZEN_ENGINE=$WORK_ROOT/build_ubuntu22.04/sim_engine
[ -x "$FROZEN_ENGINE" ] && SIM_ENGINE=${SIM_ENGINE:-$FROZEN_ENGINE}
export SIM_ENGINE=${SIM_ENGINE:-$BUILD/sim_engine}
PY=${PY:-$ENV_DIR/bin/python}
[ -f "$WORK_ROOT/carto_key" ] && export CARTO_API_KEY=$(cat "$WORK_ROOT/carto_key")
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-2}

# Final configuration of the paper: no destination code 000000000 in the demand, cost weight alpha_s = 0.25.
export NO_CODE=${NO_CODE:-1} ALPHA_S=${ALPHA_S:-0.25}
export RESULTS_DIR=${RESULTS_DIR:-$REPO/model/results}
export NO_PROVINCE_COPY=${NO_PROVINCE_COPY-1}   # model v2: trips of the province relations are not counted again in the random-end classes
export DEMAND_CONF=${DEMAND_CONF:-$REPO/article/python/revision/rerun/work/conf_nocode_v2}
export K_GRID=${K_GRID:-0.9,1.0,1.1,1.2,1.3,1.4,1.5,1.6,1.7,1.8}
[ -f "$RESULTS_DIR/demand/selected_radius" ] && export CHERRY_RADIUS_KM=${CHERRY_RADIUS_KM:-$(cat "$RESULTS_DIR/demand/selected_radius")}
