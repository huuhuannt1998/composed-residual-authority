#!/bin/bash
# Refuse to start a run the machine cannot carry.
#
# This exists because the laptop crashed with five projects running at once.
# TenantSafe's own experiments are already serialized; the danger is starting
# them while OTHER projects hold containers. That check is the point of this
# script, and it is the one that fails loudest.
cd "$(dirname "$0")/.." || exit 2
MIN_FREE_GB=${MIN_FREE_GB:-4}
MIN_DISK_GB=${MIN_DISK_GB:-20}
fail=0; warn=0
ok()   { printf "  \033[32mok\033[0m    %s\n" "$1"; }
bad()  { printf "  \033[31mFAIL\033[0m  %s\n" "$1"; fail=$((fail+1)); }
note() { printf "  \033[33mWARN\033[0m  %s\n" "$1"; warn=$((warn+1)); }

echo "=== preflight ==="

# --- docker ---------------------------------------------------------------
if docker info >/dev/null 2>&1; then ok "docker daemon responding"
else bad "docker is not responding - start Docker Desktop and re-run"; fi

# --- the crash cause: foreign containers ----------------------------------
if docker info >/dev/null 2>&1; then
  # rka-* is this project's own knowledge-base infrastructure, not a competing
  # project. Flagging it would teach the reader to ignore this warning, which is
  # the one that matters.
  foreign=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -viE '^(ts|tenantsafe|rka-)' || true)
  if [ -n "$foreign" ]; then
    note "containers from OTHER research projects are running:"
    echo "$foreign" | sed 's/^/          /'
    note "each Home Assistant instance costs 0.5-1 GB. Running TenantSafe"
    note "alongside these is what crashed the machine. Stop them first."
  else ok "no competing-project containers running"; fi
  docker ps --format '{{.Names}}' 2>/dev/null | grep -q '^rka-' \
    && ok "RKA infrastructure up (rka-server, rka-worker)" || true
  ours=$(docker ps -aq --filter 'name=ts' 2>/dev/null | wc -l | tr -d ' ')
  [ "$ours" -gt 0 ] && note "$ours leftover TenantSafe container(s) - ./experiments/teardown.sh clears them" \
                    || ok "no leftover TenantSafe containers"
fi

# --- memory ---------------------------------------------------------------
if free_mb=$(vm_stat 2>/dev/null | awk '/page size of/{ps=$8} /Pages free/{f=$3} /Pages inactive/{i=$3} END{gsub(/\./,"",f); gsub(/\./,"",i); print int((f+i)*ps/1048576)}'); then
  free_gb=$((free_mb/1024))
  if [ "$free_gb" -ge "$MIN_FREE_GB" ]; then ok "free memory ${free_gb} GB (need ${MIN_FREE_GB})"
  else bad "free memory ${free_gb} GB, need ${MIN_FREE_GB}. Close other projects first."; fi
fi

# --- disk -----------------------------------------------------------------
disk_gb=$(df -g . 2>/dev/null | awk 'NR==2{print $4}')
[ -n "$disk_gb" ] && { [ "$disk_gb" -ge "$MIN_DISK_GB" ] && ok "free disk ${disk_gb} GB" \
                       || bad "free disk ${disk_gb} GB, need ${MIN_DISK_GB}"; }

# --- images ---------------------------------------------------------------
if docker info >/dev/null 2>&1; then
  for img in homeassistant/home-assistant:2026.8.3 homeassistant/home-assistant:2026.7.4 \
             homeassistant/home-assistant:2026.6.4 homeassistant/home-assistant:2024.12 \
             openhab/openhab:4.3.2 eclipse-temurin:21-jre; do
    docker image inspect "$img" >/dev/null 2>&1 && ok "image $img" \
      || note "image $img missing - ./experiments/prepare.sh pulls it"
  done
fi

# --- ports ----------------------------------------------------------------
busy=""
for p in 8123 8131 8132 8133 8134 8135 8137 8138 8141 8142 8143 8150; do
  lsof -nP -iTCP:$p -sTCP:LISTEN >/dev/null 2>&1 && busy="$busy $p"
done
[ -n "$busy" ] && note "ports in use:$busy" || ok "all experiment ports free"

# --- python ---------------------------------------------------------------
python3 - <<'PY' 2>/dev/null && echo "  ok    python deps (aiohttp, websockets)" || { echo "  FAIL  missing python deps: pip3 install aiohttp websockets"; fail=$((fail+1)); }
import aiohttp, websockets
PY

# --- alloy ----------------------------------------------------------------
if [ -n "$ALLOY_TOOLS_DIR" ] && [ -d "$ALLOY_TOOLS_DIR/alloy-dist" ]; then ok "ALLOY_TOOLS_DIR set"
else note "ALLOY_TOOLS_DIR unset - formal experiments will be skipped"; fi

# --- rka ------------------------------------------------------------------
curl -s -m 3 -o /dev/null http://localhost:9712/api/health 2>/dev/null \
  && ok "RKA API reachable" || note "RKA API not reachable - results are still written to disk"

echo
if [ "$fail" -gt 0 ]; then
  printf "\033[31mNOT READY\033[0m - %d blocking, %d advisory\n" "$fail" "$warn"; exit 1
fi
printf "\033[32mREADY\033[0m - 0 blocking, %d advisory\n" "$warn"
[ "$warn" -gt 0 ] && echo "Advisories do not block, but read the foreign-container warning before starting."
exit 0
