#!/bin/bash
# Job wrapper: loads the shared settings and runs a command from the repository root.
#   bash hpc/job.sh <command> [args...]      (commands "python" resolve to the project environment)
set -e
. "$(dirname "$0")/config.sh"
cd "$REPO"
[ "$1" = python ] && shift && set -- "$PY" "$@"
exec "$@"
