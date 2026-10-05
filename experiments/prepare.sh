#!/bin/bash
# One-time setup: pull every image an experiment needs and fetch Alloy.
# Run this once, on a good connection, so a later run never stalls on a pull.
set -u
cd "$(dirname "$0")" || exit 2
echo "=== pulling images (one at a time, to bound memory and bandwidth) ==="
for img in homeassistant/home-assistant:2026.8.3 \
           homeassistant/home-assistant:2026.7.4 \
           homeassistant/home-assistant:2026.6.4 \
           homeassistant/home-assistant:2024.12 \
           openhab/openhab:4.3.2 \
           eclipse-temurin:21-jre; do
  if docker image inspect "$img" >/dev/null 2>&1; then
    echo "  present  $img"
  else
    echo "  pulling  $img"
    docker pull "$img" 2>&1 | tail -1
  fi
done

echo
echo "=== Alloy 6 (pinned) ==="
: "${ALLOY_TOOLS_DIR:=$HOME/.tenantsafe/tools}"
ALLOY_VER=v6.2.0
ALLOY_SHA=6b8c1cb5bc93bedfc7c61435c4e1ab6e688a242dc702a394628d9a9801edb78d
mkdir -p "$ALLOY_TOOLS_DIR"
if [ -f "$ALLOY_TOOLS_DIR/alloy.jar" ] \
   && [ "$(shasum -a 256 "$ALLOY_TOOLS_DIR/alloy.jar" | cut -d" " -f1)" = "$ALLOY_SHA" ]; then
  echo "  present  alloy.jar $ALLOY_VER (sha256 verified)"
else
  echo "  fetching alloy.jar $ALLOY_VER"
  curl -sL -m 300 -o "$ALLOY_TOOLS_DIR/alloy.jar" \
    "https://github.com/AlloyTools/org.alloytools.alloy/releases/download/$ALLOY_VER/org.alloytools.alloy.dist.jar"
  got=$(shasum -a 256 "$ALLOY_TOOLS_DIR/alloy.jar" | cut -d" " -f1)
  if [ "$got" = "$ALLOY_SHA" ]; then
    echo "  ok       sha256 verified"
    echo "$ALLOY_VER" > "$ALLOY_TOOLS_DIR/alloy.version"
  else
    echo "  FAIL     sha256 mismatch"
    echo "           expected $ALLOY_SHA"
    echo "           got      $got"
    echo "           refusing to use an unverified solver; formal results must be reproducible"
    rm -f "$ALLOY_TOOLS_DIR/alloy.jar"; exit 1
  fi
fi
echo "  version pinned deliberately: 6.2.0 reproduces every recorded verdict"
echo "  (mutation suite re-run 15/15 on 2026-08-25 against this exact jar)"
echo
echo "  Add to your shell profile:"
echo "    export ALLOY_TOOLS_DIR=$ALLOY_TOOLS_DIR"
