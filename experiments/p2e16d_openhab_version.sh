#!/bin/bash
# P2 EXPERIMENT 16d - does the openHAB result hold on the CURRENT stable line?
#
# p2e16c measured openHAB 4.3.2 (released 2024-12-15). Current stable is the 5.2
# line. A cross-platform claim resting on a two-major-old build invites the
# obvious objection, so this re-runs the identical probe against 5.2.1.
#
# Writes a NEW log. The 4.3.2 evidence is not touched.
set -eu
cd "$(dirname "$0")"
IMG=${OH_IMAGE:-openhab/openhab:5.2.1}
WORK=${WORK:-/tmp/tsohab-ver}
OUT=../results/run-logs/openhab_reps_5.2.1.log
TRIALS=${TRIALS:-5}

say() { echo "$*" | tee -a "$OUT"; }
console() { docker exec tsohab bash -c "printf '%s\nlogout\n' \"$1\" | /openhab/runtime/bin/client -p habopen 2>/dev/null" | sed 's/\x1b\[[0-9;]*m//g'; }
cleanup() { docker rm -f tsohab >/dev/null 2>&1 || true; }
trap cleanup EXIT

mkdir -p "$(dirname "$OUT")"
: > "$OUT"
say "# openHAB version replication - image $IMG"
say "# run $(date -u +%Y-%m-%dT%H:%M:%SZ)  host $(uname -sm)"
say "# baseline for comparison: results/run-logs/openhab_reps.log (openHAB 4.3.2)"
say "---"

cleanup
rm -rf "$WORK"; mkdir -p "$WORK"/{conf,userdata,addons}
docker run -d --name tsohab -p 8150:8080 \
  -v "$WORK/conf":/openhab/conf -v "$WORK/userdata":/openhab/userdata \
  -v "$WORK/addons":/openhab/addons \
  -e CRYPTO_POLICY=unlimited "$IMG" >/dev/null || { say "FATAL: container would not start"; exit 2; }
say "container up; waiting for REST"
ok=0
for i in $(seq 1 120); do
  [ "$(curl -s -m 3 -o /dev/null -w '%{http_code}' http://localhost:8150/rest/ 2>/dev/null)" = "200" ] && { ok=1; break; }
  sleep 5
done
[ "$ok" = 1 ] || { say "FATAL: REST never came up"; docker logs --tail 40 tsohab | tee -a "$OUT"; exit 2; }
say "REST up after ~$((i*5))s"
sleep 20

console "openhab:users add ohadmin AdminPass123 administrator" >/dev/null || true
console "openhab:users add ohmember MemberPass123 user" >/dev/null || true
OH_ADM=$(console "openhab:users addApiToken ohadmin admtok admin" | grep -oE 'oh\.admtok\.[A-Za-z0-9]+' | head -1 || true)
OH_MEM=$(console "openhab:users addApiToken ohmember memtok user" | grep -oE 'oh\.memtok\.[A-Za-z0-9]+' | head -1 || true)
[ -n "$OH_ADM" ] && [ -n "$OH_MEM" ] || { say "FATAL: token minting failed on $IMG (console API may have changed)"; console "openhab:users list" | tee -a "$OUT"; exit 2; }
say "tokens minted"

curl -s -X PUT "http://localhost:8150/rest/items/TsProbe" \
  -H "Authorization: Bearer $OH_ADM" -H "Content-Type: application/json" \
  -d '{"type":"Switch","name":"TsProbe","label":"TenantSafe probe"}' >/dev/null
sleep 2
curl -s -X POST "http://localhost:8150/rest/rules" \
  -H "Authorization: Bearer $OH_ADM" -H "Content-Type: application/json" \
  -d '{"uid":"tsdeputy","name":"ts deputy","triggers":[],"conditions":[],
       "actions":[{"id":"a1","type":"core.ItemCommandAction",
                   "configuration":{"itemName":"TsProbe","command":"ON"}}]}' >/dev/null
sleep 2
curl -s -H "Authorization: Bearer $OH_ADM" http://localhost:8150/rest/items/TsProbe | grep -q TsProbe \
  || { say "FATAL: probe fixture not created - the arm would measure a bare instance"; exit 2; }
say "fixture verified"
say "---"

python3 p2e16c_openhab_reps.py "$OH_ADM" "$TRIALS" 2>&1 | tee -a "$OUT"

# assert on the RESULT, not the input: the run must report a valid-trial line
grep -qE 'valid trials' "$OUT" || { say "FATAL: experiment produced no verdict"; exit 2; }
say "---"
say "done $(date -u +%Y-%m-%dT%H:%M:%SZ)"
