#!/bin/bash
# Start the platform (API, job runner and built frontend) on http://$ALPHA_HOST:$ALPHA_PORT
set -e
. "$(dirname "$0")/env.sh"
cd "$ALPHA_DIR/backend"
echo "platform: http://$ALPHA_HOST:$ALPHA_PORT  API docs: /docs  engine: $SIM_ENGINE  state: $ALPHA_STATE_DIR"
exec "$VENV/bin/uvicorn" app.asgi:app --host "$ALPHA_HOST" --port "$ALPHA_PORT" --workers 1 --timeout-graceful-shutdown 5
