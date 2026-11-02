#!/bin/bash
# Job wrapper: bash hpc/run_script.sh script.py [args...]
set -e
. "$(dirname "$0")/config.sh"

cd "$REPO"
s=$1; shift
exec "$PY" "model/analysis/$s" "$@"
