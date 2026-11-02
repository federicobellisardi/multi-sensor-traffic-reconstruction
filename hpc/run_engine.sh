#!/bin/bash
# Runs the simulator on one configuration, in its own directory.
. "$(dirname "$0")/config.sh"
cd "$(dirname "$1")" && exec "$SIM_ENGINE" "$1"
