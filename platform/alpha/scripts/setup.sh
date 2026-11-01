#!/bin/bash
# One-time setup of the alpha: Python and Node environments, frontend build. Does not touch the research environment.
set -e
. "$(dirname "$0")/env.sh"
mkdir -p "$ALPHA_TOOLS"
[ -x "$VENV/bin/python" ] || uv venv -q --python 3.12 "$VENV"
uv pip install -q --python "$VENV/bin/python" -r "$ALPHA_DIR/requirements.lock"
if ! command -v node >/dev/null || [ "$(node -p 'process.versions.node.split(".")[0]')" -lt 20 ]; then
  CONDA=$(command -v mamba || command -v conda)
  [ -n "$CONDA" ] || { echo "Node >= 20 not found and neither conda nor mamba to install it"; exit 1; }
  "$CONDA" create -y -q -p "$ALPHA_TOOLS/node" -c conda-forge 'nodejs=22'
fi
cd "$ALPHA_DIR/frontend"
npm ci --no-audit --no-fund
npm run build
[ -x "$SIM_ENGINE" ] || echo "NOTE: simulator not found at $SIM_ENGINE; build it with: bash hpc/setup.sh"
echo "setup done. Start with: bash platform/alpha/scripts/run.sh"
