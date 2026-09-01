#!/bin/bash
# TenantSafe experiment runner.
#
# Runs experiments STRICTLY ONE AT A TIME, tearing down every container before
# starting the next, and re-checking free memory between experiments. Written
# after a crash caused by five research projects holding containers at once:
# the goal is a bounded, predictable footprint rather than speed.
#
#   ./run_all.sh --list                 what exists and what has already run
#   ./run_all.sh --dry-run              show the plan, touch nothing
#   ./run_all.sh --tier 0               formal only, no containers
#   ./run_all.sh --tier 1               short runtime experiments
#   ./run_all.sh --only matrix          one experiment
#   ./run_all.sh --skip lifetime_long   everything except the 6.5 h run
#   ./run_all.sh --resume               skip whatever already succeeded
#   ./run_all.sh                        everything, longest last
#
# State lives in .run_state so an interrupted run resumes instead of restarting.
set -u
cd "$(dirname "$0")" || exit 2
ROOT="$(cd .. && pwd)"
STATE=".run_state"; LOGS="../results/run-logs"; MANIFEST="MANIFEST.tsv"
WORK="${TS_WORKDIR:-$HOME/.tenantsafe/work}"
MIN_FREE_GB=${MIN_FREE_GB:-4}
mkdir -p "$LOGS" "$WORK"; touch "$STATE"

TIER=""; ONLY=""; SKIP=""; DRY=0; RESUME=0; LIST=0
while [ $# -gt 0 ]; do
  case "$1" in
    --tier) TIER="$2"; shift 2;;
    --only) ONLY="$2"; shift 2;;
    --skip) SKIP="$SKIP $2"; shift 2;;
    --dry-run) DRY=1; shift;;
    --resume) RESUME=1; shift;;
    --list) LIST=1; shift;;
    -h|--help) sed -n '2,20p' "$0"; exit 0;;
    *) echo "unknown option: $1"; exit 2;;
  esac
done

say()  { printf "\033[1m%s\033[0m\n" "$*"; }
info() { printf "       %s\n" "$*"; }
done_ok(){ grep -qx "$1" "$STATE" 2>/dev/null; }
mark()   { echo "$1" >> "$STATE"; }

rows() { grep -v '^#' "$MANIFEST" | awk -F'\t' 'NF>1'; }

if [ "$LIST" = 1 ]; then
  say "TenantSafe experiments"
  printf "  %-20s %-5s %-5s %-7s %s\n" ID TIER CTRS EST STATUS
  rows | while IFS=$'\t' read -r id script tier ctr est res out desc; do
    st=$(done_ok "$id" && echo done || echo pending)
    printf "  %-20s %-5s %-5s %-7s %s\n" "$id" "$tier" "$ctr" "${est}m" "$st"
  done
  exit 0
fi

# ---------------------------------------------------------------- helpers
mem_gb() { vm_stat 2>/dev/null | awk '/page size of/{ps=$8} /Pages free/{f=$3} /Pages inactive/{i=$3} END{gsub(/\./,"",f);gsub(/\./,"",i);print int((f+i)*ps/1073741824)}'; }
guard() {
  local g; g=$(mem_gb)
  if [ -n "$g" ] && [ "$g" -lt "$MIN_FREE_GB" ]; then
    say "STOPPING: free memory ${g} GB fell below ${MIN_FREE_GB} GB."
    info "Nothing is lost - re-run with --resume once memory frees up."
    ./teardown.sh; exit 3
  fi
}
clean() { ./teardown.sh >/dev/null 2>&1; sleep 2; }

wait_http() { # port, expected-codes, timeout-steps
  local p=$1 want=$2 n=${3:-72}
  for i in $(seq 1 "$n"); do
    c=$(curl -s -m 3 -o /dev/null -w "%{http_code}" "http://localhost:$p/" 2>/dev/null || echo 000)
    case " $want " in *" $c "*) return 0;; esac
    sleep 5
  done
  return 1
}

up_ha() { # name port [version]
  local name=$1 port=$2 ver=${3:-2026.8.3}
  docker rm -f "$name" >/dev/null 2>&1
  rm -rf "$WORK/cfg-$name"; mkdir -p "$WORK/cfg-$name"
  docker run -d --name "$name" -p "$port":8123 -v "$WORK/cfg-$name":/config \
    -e TZ=UTC "homeassistant/home-assistant:$ver" >/dev/null || return 1
  wait_http "$port" "302 200" || { info "$name did not come up on :$port"; return 1; }
  sleep 10   # settle: the auth provider is not ready the instant HTTP answers
}

patch_ha() { # name A|B
  local name=$1 which=$2 f
  [ "$which" = A ] && f=tsmon_defenseA.py || f=tsmon_patch.py
  docker cp "$ROOT/models/$f" "$name":/tmp/ >/dev/null 2>&1
  docker exec "$name" python3 /tmp/"$f" >/dev/null 2>&1
  docker restart "$name" >/dev/null 2>&1
}

ohab_console() { docker exec tsohab bash -c "printf '%s\nlogout\n' \"$1\" | /openhab/runtime/bin/client -p habopen 2>/dev/null" | sed 's/\x1b\[[0-9;]*m//g'; }

up_ohab() {
  docker rm -f tsohab >/dev/null 2>&1
  rm -rf "$WORK/ohab"; mkdir -p "$WORK/ohab"/{conf,userdata,addons}
  docker run -d --name tsohab -p 8150:8080 \
    -v "$WORK/ohab/conf":/openhab/conf -v "$WORK/ohab/userdata":/openhab/userdata \
    -v "$WORK/ohab/addons":/openhab/addons \
    -e CRYPTO_POLICY=unlimited openhab/openhab:4.3.2 >/dev/null || return 1
  for i in $(seq 1 90); do
    [ "$(curl -s -m 3 -o /dev/null -w '%{http_code}' http://localhost:8150/rest/ 2>/dev/null)" = "200" ] && break
    sleep 5
  done
  sleep 15
  ohab_console "openhab:users add ohadmin AdminPass123 administrator" >/dev/null
  ohab_console "openhab:users add ohmember MemberPass123 user" >/dev/null
  OH_ADM=$(ohab_console "openhab:users addApiToken ohadmin admtok admin" | grep -oE 'oh\.admtok\.[A-Za-z0-9]+' | head -1)
  OH_MEM=$(ohab_console "openhab:users addApiToken ohmember memtok user" | grep -oE 'oh\.memtok\.[A-Za-z0-9]+' | head -1)
  [ -n "$OH_ADM" ] && [ -n "$OH_MEM" ] || { info "openHAB token minting failed"; return 1; }
  export OH_ADM OH_MEM
}

alloy() { # model-file out-dir
  : "${ALLOY_TOOLS_DIR:=$HOME/.tenantsafe/tools}"
  local jar=/tools/alloy.jar
  if [ ! -f "$ALLOY_TOOLS_DIR/alloy.jar" ]; then
    if [ -f "$ALLOY_TOOLS_DIR/alloy-dist/Alloy.app/Contents/Resources/org.alloytools.alloy.dist.jar" ]; then
      jar=/tools/alloy-dist/Alloy.app/Contents/Resources/org.alloytools.alloy.dist.jar
    else
      info "no Alloy jar under $ALLOY_TOOLS_DIR - run ./prepare.sh"; return 9
    fi
  fi
  local m=$1 o=$2
  rm -rf "$ROOT/$o"; mkdir -p "$ROOT/$o"
  docker run --rm -v "$ALLOY_TOOLS_DIR:/tools:ro" -v "$ROOT:/w" -w /w eclipse-temurin:21-jre \
    java -jar "$jar" exec -o "$o" "models/$m" 2>&1 | grep -v findPlatform
}

# ---------------------------------------------------------------- experiments
run_one() {
  local id=$1 log="$LOGS/$id.log"
  case "$id" in
    alloy_crd)        alloy tenantsafe_crd.als       results/tenantsafe_crd ;;
    alloy_mutants)    alloy tenantsafe_mutants.als   results/tenantsafe_mutants ;;
    alloy_depth)      alloy tenantsafe_depth.als     results/tenantsafe_depth ;;
    alloy_platforms)  alloy tenantsafe_platforms.als results/tenantsafe_platforms ;;
    scope_sweep)      ./p1e15_scope_sweep.sh ;;
    micro)            python3 p1e11b_micro.py ;;
    severity)         python3 p2e19_severity.py ;;
    residue_finder)   for s in "$ROOT"/tools/specs/*.json; do
                        echo "--- $(basename "$s")"; python3 "$ROOT/tools/residue_finder.py" "$s"; done ;;
    matrix)           up_ha tsmatrix 8136 && python3 p1e7_matrix.py 8136 "${REPS:-30}" ;;
    sessions)         up_ha tssess 8137 && python3 p1e7b_sessions.py 8137 ;;
    regression_base)  up_ha tsreg 8141 && python3 p1e12_regression.py 8141 "baseline (unpatched)" ;;
    regression_defA)  up_ha tsregA 8142 && patch_ha tsregA A && wait_http 8142 "302 200" \
                        && sleep 8 && python3 p1e12_regression.py 8142 "Defense A" ;;
    capability_matrix) up_ha tscap 8124 && python3 p0e3_capability_matrix.py 8124 ;;
    deputy_generality) up_ha tsdep 8135 && python3 p1e9_deputy_generality.py 8135 ;;
    version_study)    ./run_version_study.sh ;;
    openhab_request)  up_ohab && python3 p2e16_openhab.py "$OH_ADM" "$OH_MEM" ;;
    openhab_sse)      up_ohab && python3 p2e16b_openhab_sse.py "$OH_ADM" "$OH_MEM" ;;
    openhab_reps)     up_ohab && python3 p2e16c_openhab_reps.py "$OH_ADM" 5 ;;
    benchmark)        # THE ONLY EXPERIMENT THAT NEEDS THREE INSTANCES AT ONCE.
                      # That is deliberate: measuring the arms simultaneously with
                      # matched restart counts is what removes the confound that
                      # invalidated the first attempt. Do not serialize it.
                      up_ha tsbench0 8141 && up_ha tsbenchA 8142 && up_ha tsbenchB 8143 \
                        && patch_ha tsbenchA A && patch_ha tsbenchB B \
                        && docker restart tsbench0 >/dev/null \
                        && wait_http 8141 "302 200" && wait_http 8142 "302 200" && wait_http 8143 "302 200" \
                        && sleep 10 && python3 p1e11_benchmark.py ;;
    lifetime_long)    up_ha tslife 8138 && python3 p1e8b_lifetime_long.py ;;
    *) echo "no runner defined for '$id'"; return 2;;
  esac
}

# ---------------------------------------------------------------- plan
plan=$(rows | while IFS=$'\t' read -r id script tier ctr est res out desc; do
  [ -n "$TIER" ] && [ "$tier" != "$TIER" ] && continue
  [ -n "$ONLY" ] && [ "$id" != "$ONLY" ] && continue
  case " $SKIP " in (*" $id "*) continue;; esac
  [ "$RESUME" = 1 ] && done_ok "$id" && continue
  printf '%s\t%s\t%s\n' "$id" "$est" "$desc"
done)

[ -z "$plan" ] && { say "nothing to run"; exit 0; }
total=$(echo "$plan" | awk -F'\t' '{s+=$2} END{printf "%.1f", s/60}')
n=$(echo "$plan" | grep -c .)
say "plan: $n experiment(s), about ${total} h, one at a time"
echo "$plan" | awk -F'\t' '{printf "       %-20s %5s min  %s\n",$1,$2,$3}'
echo
[ "$DRY" = 1 ] && { say "dry run - nothing started"; exit 0; }

./preflight.sh || { say "preflight failed - not starting"; exit 1; }
echo

# ---------------------------------------------------------------- execute
start_all=$(date +%s); failed=0
while IFS=$'\t' read -r id est desc; do
  guard
  clean
  say "==> $id  (~${est} min)  $(date '+%H:%M:%S')"
  t0=$(date +%s)
  if run_one "$id" >"$LOGS/$id.log" 2>&1; then
    rc=0
  else
    rc=$?
  fi
  t1=$(date +%s); mins=$(( (t1-t0)/60 ))
  if [ "$rc" = 0 ]; then
    mark "$id"; info "done in ${mins}m  ->  $LOGS/$id.log"
    tail -3 "$LOGS/$id.log" | sed 's/^/         /'
  elif [ "$rc" = 9 ]; then
    info "skipped (missing prerequisite) - see $LOGS/$id.log"
  else
    info "FAILED rc=$rc after ${mins}m  ->  $LOGS/$id.log"
    tail -6 "$LOGS/$id.log" | sed 's/^/         /'
    info "continuing; re-run this one alone with: ./run_all.sh --only $id"
    failed=$((failed+1))
  fi
  echo
done <<< "$plan"
clean
say "run complete  ($(( ($(date +%s)-start_all)/60 )) min total)"
info "state: $STATE   logs: $LOGS"
