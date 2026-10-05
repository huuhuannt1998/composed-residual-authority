#!/bin/bash
# Run AFTER the lifetime experiment finishes. Determines whether the defence
# patches reject the admin operations the capability experiment needs for setup.
cd "$(dirname "$0")" || exit 2
pgrep -f p1e8b_lifetime_long >/dev/null && { echo "lifetime run still active - refusing to compete"; exit 1; }
export ALLOY_TOOLS_DIR="${ALLOY_TOOLS_DIR:-$HOME/.tenantsafe/tools}"
./run_all.sh --only capability_defB
./run_all.sh --only capability_defA
