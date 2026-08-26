#!/bin/bash
# P1 EXPERIMENT 15 - scope and budget sensitivity.
# Re-runs the per-platform residue suite at increasing scopes and step budgets and
# records verdict + runtime for every command, so we can say whether any NEW
# qualitative witness structure appears as the bound grows. This is a bounded
# statement about the tested model, NOT a proof over unbounded systems.
set -u
# Directory containing alloy-dist/ (Alloy 6). Download from
# https://github.com/AlloyTools/org.alloytools.alloy/releases
: "${ALLOY_TOOLS_DIR:?set ALLOY_TOOLS_DIR to a directory containing alloy-dist/}"
SP="$ALLOY_TOOLS_DIR"
JAR=/tools/alloy-dist/Alloy.app/Contents/Resources/org.alloytools.alloy.dist.jar
SRC=models/tenantsafe_platforms.als
OUT=results/scope_sweep; mkdir -p $OUT
BASE='for 4 but 3 Principal, 2 Device, 3 Grant, 2 Session, 2 Auto, 10 steps'
run_scope () {
  local tag="$1" spec="$2"
  local f="$OUT/platforms_$tag.als"
  sed "s/$BASE/$spec/g" "$SRC" > "$f"
  echo "### scope $tag :: $spec"
  /usr/bin/time -p docker run --rm -v "$SP/tools:/tools:ro" -v "$PWD:/w" -w /w \
    eclipse-temurin:21-jre java -jar $JAR exec -o "$OUT/o_$tag" "$f" 2>&1 \
    | grep -E '^[0-9]+\. |^real' | sed 's/^/    /'
  echo
}
run_scope S1 'for 4 but 3 Principal, 2 Device, 3 Grant, 2 Session, 2 Auto, 10 steps'
run_scope S2 'for 5 but 4 Principal, 3 Device, 4 Grant, 3 Session, 3 Auto, 12 steps'
run_scope S3 'for 6 but 5 Principal, 4 Device, 5 Grant, 4 Session, 4 Auto, 14 steps'
run_scope S4 'for 7 but 6 Principal, 4 Device, 6 Grant, 5 Session, 5 Auto, 16 steps'
