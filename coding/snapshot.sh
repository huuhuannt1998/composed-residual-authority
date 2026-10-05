#!/bin/bash
# E1.8 / mitigation C1 — snapshot every documentation source with a content hash.
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
OUT=coding/snapshots; MAN=coding/snapshots/MANIFEST.tsv
: > $MAN
printf "url\thttp\tbytes\tsha256\tretrieved_utc\n" >> $MAN
while IFS= read -r u; do
  [ -z "$u" ] && continue
  f=$OUT/$(echo "$u" | shasum -a 256 | cut -c1-16).html
  code=$(curl -sL -A "$UA" -m 25 -o "$f" -w "%{http_code}" "$u" 2>/dev/null || echo 000)
  if [ -s "$f" ]; then b=$(wc -c < "$f" | tr -d ' '); h=$(shasum -a 256 "$f" | cut -d' ' -f1); else b=0; h="-"; fi
  printf "%s\t%s\t%s\t%s\t%s\n" "$u" "$code" "$b" "$h" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> $MAN
done < coding/sources.txt
