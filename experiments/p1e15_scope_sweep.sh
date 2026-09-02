#!/bin/bash
# P1 EXPERIMENT 15 - scope and budget sensitivity.
# Re-runs the per-platform residue suite at increasing scopes and step budgets and
# records verdict + runtime for every command, so we can say whether any NEW
# qualitative witness structure appears as the bound grows. This is a bounded
# statement about the tested model, NOT a proof over unbounded systems.
set -eu
cd "$(dirname "$0")/.."          # paths below are relative to the repo root
# Directory containing alloy-dist/ (Alloy 6). Download from
# https://github.com/AlloyTools/org.alloytools.alloy/releases
: "${ALLOY_TOOLS_DIR:=$HOME/.tenantsafe/tools}"
SP="$ALLOY_TOOLS_DIR"
JAR=/tools/alloy.jar
SRC=models/tenantsafe_platforms.als
[ -f "$SRC" ] || { echo "FATAL: $SRC not found (cwd $PWD)" >&2; exit 2; }
OUT=results/scope_sweep; mkdir -p $OUT
BASE='for 4 but 3 Principal, 2 Device, 3 Grant, 2 Session, 2 Auto, 10 steps'
run_scope () {
  local tag="$1" spec="$2"
  local f="$OUT/platforms_$tag.als"
  sed "s/$BASE/$spec/g" "$SRC" > "$f"
  # An empty or unsubstituted model would let Alloy "succeed" with zero commands,
  # which is how this failed silently once already.
  [ -s "$f" ] || { echo "FATAL: generated $f is empty" >&2; exit 2; }
  grep -q "$spec" "$f" || { echo "FATAL: scope substitution did not apply in $f" >&2; exit 2; }
  echo "### scope $tag :: $spec"
  # $SP IS the tools directory; mounting "$SP/tools" created an empty mount, so
  # java found no jar and died in 0.5s. The old grep then swallowed the error and
  # the step looked successful. Keep the raw output and assert on the RESULT.
  # Alloy refuses to write into a non-empty output directory and exits without
  # solving. Leftovers from a previous run are therefore a silent no-op.
  rm -rf "$OUT/o_$tag"
  local raw="$OUT/raw_$tag.txt"
  /usr/bin/time -p docker run --rm -v "$SP:/tools:ro" -v "$PWD:/w" -w /w \
    eclipse-temurin:21-jre java -jar $JAR exec -o "$OUT/o_$tag" "$f" >"$raw" 2>&1 || true
  grep -E '^[0-9]+\. |^real' "$raw" | sed 's/^/    /'
  local n
  n=$(grep -cE '^[0-9]+\. +(run|check) ' "$raw" || true)
  if [ "$n" -lt 17 ]; then
    echo "FATAL: scope $tag produced $n verdicts, expected 17. First lines of output:" >&2
    head -5 "$raw" >&2
    exit 2
  fi
  echo "    -> $n verdicts"
  echo
}
run_scope S1 'for 4 but 3 Principal, 2 Device, 3 Grant, 2 Session, 2 Auto, 10 steps'
run_scope S2 'for 5 but 4 Principal, 3 Device, 4 Grant, 3 Session, 3 Auto, 12 steps'
run_scope S3 'for 6 but 5 Principal, 4 Device, 5 Grant, 4 Session, 4 Auto, 14 steps'
run_scope S4 'for 7 but 6 Principal, 4 Device, 6 Grant, 5 Session, 5 Auto, 16 steps'
