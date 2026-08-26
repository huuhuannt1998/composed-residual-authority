#!/bin/bash
# P1 Exp 6 driver: fresh unpatched instance per version.
SP="${TS_WORKDIR:-$(mktemp -d)}"   # per-version Home Assistant config roots
cd "$(dirname "$0")"
run() {
  VER=$1; PORT=$2; NAME="tsver-$(echo $VER | tr '.' '-')"
  echo "########## $VER on :$PORT ##########"
  docker rm -f $NAME >/dev/null 2>&1
  rm -rf $SP/cfg-$NAME && mkdir -p $SP/cfg-$NAME
  docker run -d --name $NAME -p $PORT:8123 -v $SP/cfg-$NAME:/config -e TZ=UTC \
    homeassistant/home-assistant:$VER >/dev/null
  for i in $(seq 1 60); do
    c=$(curl -s -m 3 -o /dev/null -w "%{http_code}" http://localhost:$PORT/ 2>/dev/null || echo 000)
    [ "$c" = "302" ] || [ "$c" = "200" ] && { echo "  up after $((i*5))s"; break; }
    sleep 5
  done
  sleep 12
  python3 p1e6_version_study.py $PORT $VER 2>&1 | tail -12
  docker rm -f $NAME >/dev/null 2>&1
  rm -rf $SP/cfg-$NAME
}
run 2024.12  8131
run 2026.6.4 8132
run 2026.7.4 8133
run 2026.8.3 8134
echo "########## VERSION STUDY COMPLETE ##########"
