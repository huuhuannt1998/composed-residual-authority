#!/bin/bash
# Remove every container and config root this project creates. Safe to run at
# any time; it never touches rka-* infrastructure or other projects.
KEEP_RKA=1
names=$(docker ps -aq --filter 'name=ts' 2>/dev/null)
[ -n "$names" ] && docker rm -f $names >/dev/null 2>&1
n=$(echo "$names" | grep -c . 2>/dev/null || echo 0)
echo "  removed $n TenantSafe container(s)"
for d in "${TS_WORKDIR:-/tmp}"/cfg-* ./cfg-* ../cfg-*; do
  [ -d "$d" ] && rm -rf "$d" && echo "  removed config root $d"
done
docker ps --format '{{.Names}}' | grep -q '^rka-' && echo "  rka-* infrastructure left running (required)"
exit 0
