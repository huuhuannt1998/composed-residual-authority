#!/bin/bash
# Homebridge UI arm with a delivered-event baseline (D1 review, F-08), 2026-10-03.
# The image is pinned BY DIGEST (the original arm used the unpinned `latest` tag and
# did not record which build it ran). Each trial gets a fresh container and volume.
#   ./replicate_homebridge_2026-10-03.sh <reps> [tag]
set -u
cd "$(dirname "$0")" || exit 2
ROOT="$(cd .. && pwd)"
REPS=${1:-5}; TAG=${2:-r}
IMG="homebridge/homebridge@sha256:77c685a40911b3b95448f3550be0c8b94cd7b4e66daecc1cc39a8285be75b245"
OUT="$ROOT/results/replication_2026-10-03"
WORK="${TS_WORKDIR:-$HOME/.tenantsafe/work}/rep-2026-10-03"
mkdir -p "$OUT" "$WORK"
MAN="$OUT/manifest_homebridge.log"
note() { echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] $*" | tee -a "$MAN"; }

up_hb() { # identical setup to run_all.sh up_homebridge, except the pinned image
  docker rm -f tsrephb >/dev/null 2>&1
  rm -rf "$WORK/hb"; mkdir -p "$WORK/hb"
  docker run -d --name tsrephb -m 1g -p 8191:8581 -v "$WORK/hb":/homebridge \
    -e HOMEBRIDGE_CONFIG_UI=1 "$IMG" >/dev/null || return 1
  for i in $(seq 1 60); do
    c=$(curl -s -m 3 -o /dev/null -w '%{http_code}' http://localhost:8191/ 2>/dev/null)
    case "$c" in 200|302) break;; esac; sleep 5; done
  local code
  for i in $(seq 1 20); do
    code=$(curl -s -m 8 -o /dev/null -w '%{http_code}' -X POST http://localhost:8191/api/setup-wizard/create-first-user \
      -H 'Content-Type: application/json' \
      -d '{"username":"tsadmin","password":"AdminPass123","name":"TS Admin","admin":true}')
    [ "$code" = "201" ] && break; sleep 5; done
  [ "$code" = "201" ] || { note "setup wizard did not create tsadmin (http $code)"; return 1; }
  # wait until the Homebridge server itself (not only the UI) reports up, so the
  # restart stimulus starts from a settled state
  local tok st
  tok=$(curl -s -m 8 -X POST http://localhost:8191/api/auth/login -H 'Content-Type: application/json' \
    -d '{"username":"tsadmin","password":"AdminPass123"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
  for i in $(seq 1 40); do
    st=$(curl -s -m 5 -H "Authorization: Bearer $tok" http://localhost:8191/api/status/homebridge)
    case "$st" in *'"up"'*|*'"ok"'*) break;; esac; sleep 3; done
  note "homebridge server status at start: $st"
}

note "homebridge stream start, reps=$REPS, image $IMG"
note "image id $(docker image inspect "$IMG" --format '{{.Id}}')"
note "image manifest: $(docker run --rm --entrypoint sh "$IMG" -c "grep -E 'Release Version|Homebridge UI|Homebridge\\|' /opt/homebridge/Docker.manifest" | tr -s ' \n' ' ')"
for r in $(seq 1 "$REPS"); do
  note "trial $TAG$r: start"
  if up_hb; then
    python3 p2e17b_homebridge_delivered.py http://localhost:8191 "$OUT/homebridge_$TAG$r.json" > "$OUT/homebridge_$TAG$r.log" 2>&1
    note "trial $TAG$r: rc=$?"
    docker logs tsrephb > "$OUT/homebridge_${TAG}${r}_container.log" 2>&1
  else note "trial $TAG$r: CONTAINER FAILED"; fi
  docker rm -f tsrephb >/dev/null 2>&1; rm -rf "$WORK/hb"
done
note "homebridge stream done"
