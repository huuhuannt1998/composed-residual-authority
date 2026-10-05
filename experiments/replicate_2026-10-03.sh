#!/bin/bash
# Replication of the single-run arms flagged by the D1 review (finding F-03),
# 2026-10-03. Every arm calls the ORIGINAL experiment script unchanged; only the
# container lifecycle and the output locations are new, so that no earlier result
# file is overwritten. Each repetition gets a FRESH Home Assistant 2026.8.3
# container and a fresh configuration root, exactly as run_all.sh does.
#
#   ./replicate_2026-10-03.sh A <reps>   auditor (p1e21), sessions (p1e7b), third-party (p1e18)
#   ./replicate_2026-10-03.sh B <reps>   capability matrix (p0e3) under baseline, defense B, defense A
#   ./replicate_2026-10-03.sh R <reps>   lifecycle regression suite (p1e12) under the same three conditions
#
# Streams A and B use disjoint ports and container names, so they can run side by
# side (two 1 GB-capped containers at most). Neither stream calls teardown.sh,
# which would remove the other stream's container.
set -u
cd "$(dirname "$0")" || exit 2
ROOT="$(cd .. && pwd)"
STREAM=${1:?stream A or B}; REPS=${2:-5}
OUT="$ROOT/results/replication_2026-10-03"
WORK="${TS_WORKDIR:-$HOME/.tenantsafe/work}/rep-2026-10-03"
VER=2026.8.3
mkdir -p "$OUT" "$WORK"
MAN="$OUT/manifest_stream$STREAM.log"
note() { echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] $*" | tee -a "$MAN"; }

wait_http() { local p=$1 n=${2:-72}
  for i in $(seq 1 "$n"); do
    c=$(curl -s -m 3 -o /dev/null -w "%{http_code}" "http://localhost:$p/" 2>/dev/null || echo 000)
    case "$c" in 302|200) return 0;; esac; sleep 5; done; return 1; }
wait_auth() { local p=$1 n=${2:-40} body
  for i in $(seq 1 "$n"); do
    body=$(curl -s -m 5 -X POST "http://localhost:$p/auth/login_flow" -H 'Content-Type: application/json' \
      -d "{\"client_id\":\"http://localhost:$p/\",\"handler\":[\"homeassistant\",null],\"redirect_uri\":\"http://localhost:$p/\",\"type\":\"authorize\"}" 2>/dev/null)
    case "$body" in *flow_id*) return 0;; esac; sleep 3; done; return 1; }
up_ha() { # name port -> config root path on stdout-free global CFGDIR
  local name=$1 port=$2
  docker rm -f "$name" >/dev/null 2>&1
  CFGDIR="$WORK/cfg-$name"; rm -rf "$CFGDIR"; mkdir -p "$CFGDIR"
  docker run -d --name "$name" -m 1g -p "$port":8123 -v "$CFGDIR":/config -e TZ=UTC \
    "homeassistant/home-assistant:$VER" >/dev/null || return 1
  wait_http "$port" || { note "$name did not come up on :$port"; return 1; }
  wait_auth "$port" || { note "$name auth never ready on :$port"; return 1; }
}
patch_ha() { # name A|B   (identical to run_all.sh)
  local name=$1 which=$2 f
  [ "$which" = A ] && f=tsmon_defenseA.py || f=tsmon_patch.py
  docker cp "$ROOT/models/$f" "$name":/tmp/ >/dev/null 2>&1
  docker exec "$name" python3 /tmp/"$f" 2>&1 | tee -a "$MAN"
  docker restart "$name" >/dev/null 2>&1
  sleep 5
}
down() { docker rm -f "$1" >/dev/null 2>&1; rm -rf "$WORK/cfg-$1"; }

note "stream $STREAM start, reps=$REPS, image homeassistant/home-assistant:$VER"
note "image id $(docker image inspect homeassistant/home-assistant:$VER --format '{{.Id}}')"
note "python $(python3 --version 2>&1); $(python3 -c 'import websockets,aiohttp;print("websockets",websockets.__version__,"aiohttp",aiohttp.__version__)')"

for r in $(seq 1 "$REPS"); do
  if [ "$STREAM" = A ]; then
    # --- configuration auditor (p1e21), fresh instance ------------------------
    note "rep $r auditor: start"
    if up_ha tsrepaud 8197; then
      python3 p1e21_auditor_rerun.py "$CFGDIR" 8197 "$OUT/auditor_r$r" > "$OUT/auditor_r${r}_stdout.log" 2>&1
      note "rep $r auditor: rc=$?"
    else note "rep $r auditor: CONTAINER FAILED"; fi
    down tsrepaud
    # --- session-condition arms A1-A5 (p1e7b), fresh instance ------------------
    note "rep $r sessions: start"
    if up_ha tsrepsess 8137; then
      rm -f /tmp/p1e7b.json
      python3 p1e7b_sessions.py 8137 > "$OUT/sessions_r$r.log" 2>&1
      note "rep $r sessions: rc=$?"
      [ -f /tmp/p1e7b.json ] && cp /tmp/p1e7b.json "$OUT/sessions_r$r.json"
    else note "rep $r sessions: CONTAINER FAILED"; fi
    down tsrepsess
    # --- third-party long-lived token arm (p1e18), fresh instance --------------
    note "rep $r thirdparty: start"
    if up_ha tsreptpc 8193; then
      python3 p1e18_thirdparty_carrier.py 8193 > "$OUT/thirdparty_r$r.log" 2>&1
      note "rep $r thirdparty: rc=$?"
    else note "rep $r thirdparty: CONTAINER FAILED"; fi
    down tsreptpc
  elif [ "$STREAM" = R ]; then
    # --- lifecycle regression suite (p1e12) under the three conditions --------
    # Same port and label per condition as run_all.sh; arm order rotates.
    case $((r % 3)) in 1) arms="base defB defA";; 2) arms="defB defA base";; 0) arms="defA base defB";; esac
    for arm in $arms; do
      case $arm in base) port=8141; lab="baseline (unpatched)";; defA) port=8142; lab="Defense A";; defB) port=8143; lab="Defense B";; esac
      note "rep $r regression $arm: start"
      if up_ha tsrepreg "$port"; then
        ok=1
        case $arm in
          defA) patch_ha tsrepreg A; wait_http "$port" && wait_auth "$port" || ok=0;;
          defB) patch_ha tsrepreg B; wait_http "$port" && wait_auth "$port" || ok=0;;
        esac
        if [ $ok = 1 ]; then
          rm -f "/tmp/p1e12_$port.json"
          python3 p1e12_regression.py "$port" "$lab" > "$OUT/regression_${arm}_r$r.log" 2>&1
          note "rep $r regression $arm: rc=$?"
          [ -f "/tmp/p1e12_$port.json" ] && cp "/tmp/p1e12_$port.json" "$OUT/regression_${arm}_r$r.json"
        else note "rep $r regression $arm: PATCHED INSTANCE NOT READY"; fi
      else note "rep $r regression $arm: CONTAINER FAILED"; fi
      down tsrepreg
    done
  else
    # --- capability matrix (p0e3) under the three conditions -------------------
    # p0e3 hard-codes port 8124. Arm order rotates per repetition.
    case $((r % 3)) in 1) arms="baseline defenseB defenseA";; 2) arms="defenseB defenseA baseline";; 0) arms="defenseA baseline defenseB";; esac
    for arm in $arms; do
      note "rep $r capability $arm: start"
      if up_ha tsrepcap 8124; then
        ok=1
        case $arm in
          defenseA) patch_ha tsrepcap A; wait_http 8124 && wait_auth 8124 || ok=0;;
          defenseB) patch_ha tsrepcap B; wait_http 8124 && wait_auth 8124 || ok=0;;
        esac
        if [ $ok = 1 ]; then
          rm -f "/tmp/matrix_$arm.json"
          python3 p0e3_capability_matrix.py "$arm" > "$OUT/capability_${arm}_r$r.log" 2>&1
          note "rep $r capability $arm: rc=$?"
          [ -f "/tmp/matrix_$arm.json" ] && cp "/tmp/matrix_$arm.json" "$OUT/capability_${arm}_r$r.json"
        else note "rep $r capability $arm: PATCHED INSTANCE NOT READY"; fi
      else note "rep $r capability $arm: CONTAINER FAILED"; fi
      down tsrepcap
    done
  fi
done
note "stream $STREAM done"
