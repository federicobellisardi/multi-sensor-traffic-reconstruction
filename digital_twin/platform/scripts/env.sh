# Shared settings of the alpha scripts (source it). Reuses hpc/config.sh for the simulator and the
# research environment; local overrides go in digital_twin/platform/.env (git-ignored, see .env.example).
ALPHA_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
. "$ALPHA_DIR/../../hpc/config.sh"
[ -f "$ALPHA_DIR/.env" ] && { set -a; . "$ALPHA_DIR/.env"; set +a; }
export SIM_ENGINE SIM_RUNS PY
export ALPHA_TOOLS=${ALPHA_TOOLS:-$WORK_ROOT/alpha}       # Python and Node environments
export ALPHA_STATE_DIR=${ALPHA_STATE_DIR:-$ALPHA_TOOLS/state}  # database and run directories
export ALPHA_RESEARCH_PYTHON=${ALPHA_RESEARCH_PYTHON:-$PY}
export ALPHA_HOST=${ALPHA_HOST:-127.0.0.1} ALPHA_PORT=${ALPHA_PORT:-8765}
export VENV=$ALPHA_TOOLS/venv
export PATH="$ALPHA_TOOLS/node/bin:$VENV/bin:$PATH"
# caches outside the home directory, which may be small
export UV_CACHE_DIR=${UV_CACHE_DIR:-$WORK_ROOT/.cache/uv} npm_config_cache=${npm_config_cache:-$WORK_ROOT/.cache/npm}
