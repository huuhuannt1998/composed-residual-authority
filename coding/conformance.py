"""E0.7 — cross-encoding conformance on the SHARED FRAGMENT (amended C7).

Whole-model conformance is inapplicable: the Alloy and Tamarin encodings deliberately
cover different systems after the Tamarin arm was narrowed to DNA. Their ONLY overlap
is the capability lattice and the delegation-narrowing rule built on it. This checks
that the two encodings define the SAME dominance relation, which is the precondition
for the DNA result (Tamarin) to say anything about the residue results (Alloy).
"""
import re, sys, itertools
CAPS = ["View","Operate","Manage","Administer"]

als = open("models/tenantsafe_platforms.als").read()
m = re.search(r"fun dominates\s*:\s*Cap\s*->\s*Cap\s*\{(.*?)\}", als, re.S)
alloy_pairs = set()
for a,b in re.findall(r"(\w+)\s*->\s*(\w+)", m.group(1)):
    if a in CAPS and b in CAPS: alloy_pairs.add((a,b))

sp = open("models/tenantsafe_dna.spthy").read()
m2 = re.search(r"restriction cap_order:(.*?)\"\s*\n", sp, re.S)
body = m2.group(1)
tam_pairs = set()
if "held = need" in body:
    for c in CAPS: tam_pairs.add((c,c))
for a,b in re.findall(r"held\s*=\s*'(\w+)'\s*&\s*need\s*=\s*'(\w+)'", body):
    tam_pairs.add((a,b))

print("=== SHARED-FRAGMENT CONFORMANCE (amended C7) ===")
print(f"  Alloy   `dominates`  : {len(alloy_pairs)} pairs")
print(f"  Tamarin `cap_order`  : {len(tam_pairs)} pairs")
only_a = alloy_pairs - tam_pairs
only_t = tam_pairs - alloy_pairs
print(f"  only in Alloy        : {sorted(only_a) if only_a else 'none'}")
print(f"  only in Tamarin      : {sorted(only_t) if only_t else 'none'}")

tests, fails = [], 0
for held, need in itertools.product(CAPS, CAPS):          # 16 lattice tests
    a = (held,need) in alloy_pairs
    t = (held,need) in tam_pairs
    ok = (a == t); fails += (not ok)
    tests.append((f"dominates({held},{need})", a, t, ok))
# 4 delegation-chain tests: transitivity of the shared relation
chains = [("Administer","Manage","Operate"),("Administer","Manage","View"),
          ("Manage","Operate","View"),("Administer","Operate","View")]
for x,y,z in chains:
    a = ((x,y) in alloy_pairs and (y,z) in alloy_pairs and (x,z) in alloy_pairs)
    t = ((x,y) in tam_pairs   and (y,z) in tam_pairs   and (x,z) in tam_pairs)
    ok = (a == t and a); fails += (not ok)
    tests.append((f"chain {x}->{y}->{z}", a, t, ok))

print(f"\n  {'test':34s} {'alloy':>6} {'tamarin':>8}  ok")
for n,a,t,ok in tests: print(f"  {n:34s} {str(a):>6} {str(t):>8}  {'PASS' if ok else 'FAIL'}")
print(f"\n  RESULT: {len(tests)-fails}/{len(tests)} agree  ->  {'PASS' if fails==0 else 'FAIL'}")
print("  Scope limitation: conformance covers the capability lattice + delegation")
print("  narrowing ONLY. Residue channels (session, automation) exist solely in Alloy;")
print("  unbounded chain induction exists solely in Tamarin. Neither is cross-checked.")
sys.exit(1 if fails else 0)
