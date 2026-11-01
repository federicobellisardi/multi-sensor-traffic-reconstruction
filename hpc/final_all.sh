#!/bin/bash
# Full analysis on the final simulations.
set -e
bash "$(dirname "$0")/pipeline.sh"
bash "$(dirname "$0")/after_final.sh"
