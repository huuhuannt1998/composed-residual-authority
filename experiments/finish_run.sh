#!/bin/bash
# Runs everything still outstanding once the long lifetime experiment finishes.
# Waits rather than competing with it, so the timing measurement stays clean.
cd "$(dirname "$0")" || exit 2
export ALLOY_TOOLS_DIR="${ALLOY_TOOLS_DIR:-$HOME/.tenantsafe/tools}"
echo "waiting for the in-flight run to finish..."
while pgrep -f 'run_all.sh' >/dev/null; do sleep 60; done
echo "in-flight run finished at $(date '+%H:%M:%S'); starting the remainder"
exec ./run_all.sh --resume
