#!/bin/bash
# Backend (real engine included when built), frontend unit tests and browser end-to-end tests.
set -e
. "$(dirname "$0")/env.sh"
(cd "$ALPHA_DIR/backend" && "$VENV/bin/python" -m pytest -q)
cd "$ALPHA_DIR/frontend"
npm test
npm run build
npm run e2e
