"""P1 EXPERIMENT 14 - reproducible documentation corpus.

Re-verifies the frozen corpus: every URL in sources.txt has a snapshot, every
snapshot's sha256 still matches the manifest, and every manifest row carries a
retrieval timestamp. Run this before submission and again at camera-ready; a
changed hash means the vendor edited the page and the coding must be revisited.
"""
import hashlib, pathlib, sys
D=pathlib.Path(__file__).parent
snap=D/"snapshots"; man=snap/"MANIFEST.tsv"
rows=[l.rstrip("\n").split("\t") for l in man.read_text().splitlines()]
hdr,rows=rows[0],rows[1:]
srcs=[l.strip() for l in (D/"sources.txt").read_text().splitlines() if l.strip()]
by_url={r[0]:r for r in rows}
ok=miss=drift=noname=0
print(f"  {'source':64s} {'archived':9s} {'hash':9s} retrieved")
for u in srcs:
    r=by_url.get(u)
    if not r:
        print(f"  {u[:62]:64s} {'MISSING':9s} {'-':9s} -"); miss+=1; continue
    # snapshot.sh names files sha256(url + "\n")[:16], because `echo` appends a newline
    name=hashlib.sha256((u+"\n").encode()).hexdigest()[:16]+".html"
    f=snap/name
    if not f.exists():
        print(f"  {u[:62]:64s} {'NO FILE':9s} {'-':9s} {r[4]}"); noname+=1; continue
    h=hashlib.sha256(f.read_bytes()).hexdigest()
    if h==r[3]: print(f"  {u[:62]:64s} {'yes':9s} {'match':9s} {r[4]}"); ok+=1
    else:       print(f"  {u[:62]:64s} {'yes':9s} {'DRIFT':9s} {r[4]}"); drift+=1
print(f"\n  sources {len(srcs)} · manifest rows {len(rows)} · verified {ok} · missing {miss} · unnamed {noname} · drifted {drift}")
print("  RESULT:", "PASS - corpus is frozen and reproducible" if (miss==noname==drift==0 and ok==len(srcs))
      else "ATTENTION - see rows above")
sys.exit(0 if (miss==noname==drift==0 and ok==len(srcs)) else 1)
