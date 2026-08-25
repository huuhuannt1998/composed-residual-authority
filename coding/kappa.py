"""E1.9/E1.10 — determinacy coding reliability.
Pass 1: the original M1 harvest labels (2026-08-19).
Pass 2: blind re-code from cell EVIDENCE ONLY, applying coding/codebook.md strictly,
        without consulting pass-1 labels.
NOTE ON VALIDITY: both passes are by the SAME analyst. This measures INTRA-rater
(test-retest) reliability. It is NOT inter-rater reliability and must not be reported
as such; true inter-rater requires a second independent analyst.
"""
import itertools, math

PLATFORMS = ["GoogleHome","Alexa","SmartThings","HomeAssistant"]
TRANSITIONS = ["grant","delegate","expire","evict","transfer","factory_reset"]

pass1 = {  # from m1_jobb_semantics_harvest.md determinacy table
 ("GoogleHome","grant"):"D",   ("GoogleHome","delegate"):"D", ("GoogleHome","expire"):"D",
 ("GoogleHome","evict"):"D",   ("GoogleHome","transfer"):"D", ("GoogleHome","factory_reset"):"D",
 ("Alexa","grant"):"D",        ("Alexa","delegate"):"S",      ("Alexa","expire"):"S",
 ("Alexa","evict"):"C",        ("Alexa","transfer"):"S",      ("Alexa","factory_reset"):"S",
 ("SmartThings","grant"):"D",  ("SmartThings","delegate"):"D",("SmartThings","expire"):"S",
 ("SmartThings","evict"):"D",  ("SmartThings","transfer"):"C",("SmartThings","factory_reset"):"D",
 ("HomeAssistant","grant"):"D",("HomeAssistant","delegate"):"D",("HomeAssistant","expire"):"D",
 ("HomeAssistant","evict"):"D",("HomeAssistant","transfer"):"S",("HomeAssistant","factory_reset"):"S",
}

pass2 = {  # blind re-code, codebook applied strictly
 ("GoogleHome","grant"):"D",   ("GoogleHome","delegate"):"D", ("GoogleHome","expire"):"D",
 ("GoogleHome","evict"):"D",   ("GoogleHome","transfer"):"D", ("GoogleHome","factory_reset"):"D",
 ("Alexa","grant"):"D",        ("Alexa","delegate"):"S",      ("Alexa","expire"):"S",
 ("Alexa","evict"):"C",        ("Alexa","transfer"):"S",      ("Alexa","factory_reset"):"S",
 ("SmartThings","grant"):"D",  ("SmartThings","delegate"):"D",("SmartThings","expire"):"S",
 # DISAGREEMENT: evict IS documented ("won't be able to control any of its devices")
 # but member-authored Routines are NOT addressed, and the two readings differ.
 # Codebook says that is C, not D. Pass 1 coded D.
 ("SmartThings","evict"):"C",  ("SmartThings","transfer"):"C",("SmartThings","factory_reset"):"D",
 ("HomeAssistant","grant"):"D",("HomeAssistant","delegate"):"D",("HomeAssistant","expire"):"D",
 ("HomeAssistant","evict"):"D",("HomeAssistant","transfer"):"S",("HomeAssistant","factory_reset"):"S",
}

cells = [(p,t) for p in PLATFORMS for t in TRANSITIONS]
LAB = ["D","C","S"]
n = len(cells)

cm = {(a,b):0 for a in LAB for b in LAB}
for c in cells: cm[(pass1[c], pass2[c])] += 1

po = sum(cm[(l,l)] for l in LAB)/n
m1 = {l: sum(1 for c in cells if pass1[c]==l) for l in LAB}
m2 = {l: sum(1 for c in cells if pass2[c]==l) for l in LAB}
pe = sum(m1[l]*m2[l] for l in LAB)/(n*n)
kappa = (po-pe)/(1-pe)
se = math.sqrt(po*(1-po)/(n*(1-pe)**2))
# The normal approximation can put the upper bound above 1; kappa is bounded by 1
# by construction, so the interval is clamped. The unclamped value is kept for audit.
lo_raw, hi_raw = kappa-1.96*se, kappa+1.96*se
lo, hi = max(-1.0, lo_raw), min(1.0, hi_raw)

print("=== CONFUSION MATRIX (rows pass1, cols pass2) ===")
print("        " + "".join(f"{b:>5}" for b in LAB))
for a in LAB: print(f"  {a:5s} " + "".join(f"{cm[(a,b)]:5d}" for b in LAB))
print(f"\n  pass1 marginals: {m1}")
print(f"  pass2 marginals: {m2}")
print(f"\n  n cells              = {n}")
print(f"  observed agreement Po= {po:.4f}  ({sum(cm[(l,l)] for l in LAB)}/{n})")
print(f"  expected agreement Pe= {pe:.4f}")
print(f"  Cohen's kappa        = {kappa:.4f}   95% CI [{lo:.4f}, {hi:.4f}]"
      + (f"  (unclamped upper {hi_raw:.4f})" if hi_raw > 1 else ""))
print(f"  threshold 0.70       : {'PASS' if kappa>=0.70 else 'FAIL'}")
print("\n=== DISAGREEMENTS ===")
for c in cells:
    if pass1[c]!=pass2[c]: print(f"  {c[0]:14s} {c[1]:14s} pass1={pass1[c]}  pass2={pass2[c]}")
print("\n=== CORRECTED TALLY (pass 2, codebook-strict) ===")
print(f"  D={m2['D']}  C={m2['C']}  S={m2['S']}   (pass1 was D={m1['D']} C={m1['C']} S={m1['S']})")
print("\n  NOTE: intra-rater (test-retest), SAME analyst. NOT inter-rater reliability.")
