"""E3.1/E3.2/E3.6/E3.7 — compile the Stage 3 gate verdict from all executed runs.
Every row cites the run or experiment that produced it. Predeclared thresholds
(design section 9.4) are applied as written; none were changed after seeing results."""

# (platform, transition, property, reading) -> verdict, evidence, level, severity, crd
R = [
 # --- RC: revocation-completeness across `evict` ---
 ("HomeAssistant","evict","RC","documented(L3)","FALSIFIED","E7.6 deputy: fire_event -> automation -> actuation","L3","S3",2),
 ("HomeAssistant","evict","RC","documented(L3)","FALSIFIED","E7.4 read residue: non-empty get_states in 30/30 runs + live events","L3","S2",2),
 ("GoogleHome","evict","RC","A sessions cascade","HOLDS","GHA_sess_act UNSAT","L0/L1","S0",None),
 ("GoogleHome","evict","RC","B sessions persist","FALSIFIED","GHB_sess_act SAT","L0/L1","S3",1),
 ("GoogleHome","evict","RC","documented","FALSIFIED","R1 lock passcode survives removal (documented)","L0","S4",1),
 ("GoogleHome","evict","RC","documented","FALSIFIED","R2 Google TV account persists (documented)","L0","S2",1),
 ("Alexa","evict","RC","AA","HOLDS","ALXAA_sess_act UNSAT","L0","S0",None),
 ("Alexa","evict","RC","AB","FALSIFIED","ALXAB_sess_act SAT","L0","S3",1),
 ("Alexa","evict","RC","BA","HOLDS","ALXBA_sess_act UNSAT","L0","S0",None),
 ("Alexa","evict","RC","BB","FALSIFIED","ALXBB_sess_act SAT","L0","S3",1),
 ("SmartThings","evict","RC","A Routines cascade","FALSIFIED","STA_auto_act SAT; STA_foreign_act SAT","L0","S3",2),
 ("SmartThings","evict","RC","B Routines persist","FALSIFIED","STB_auto_act SAT","L0","S3",2),
 # --- NRT: transfer, both directions ---
 ("*","transfer","NRT-A","wipe","HOLDS","NRT_A_priorOwner_wipes UNSAT","model","S0",None),
 ("*","transfer","NRT-A","no wipe","FALSIFIED","NRT_A_priorOwner_no_wipe SAT","model","S3",1),
 ("*","transfer","NRT-B","wipe","HOLDS","NRT_B_history_wipes UNSAT","model","S0",None),
 ("*","transfer","NRT-B","no wipe","FALSIFIED","NRT_B_history_no_wipe SAT","model","S2",1),
 # --- GTB ---
 ("*","expire","GTB","expiry cascades session","HOLDS","GTB_holds_when_expiry_cascades UNSAT","model","S0",None),
 ("*","expire","GTB","no cascade","FALSIFIED","GTB_fails_when_no_cascade SAT","model","S3",1),
 # --- DNA ---
 ("*","delegate","DNA-capability","-","HOLDS","Tamarin verified, 543 steps, use_induction","model","S0",None),
 ("*","delegate","DNA-device","-","FALSIFIED","Tamarin 8-step trace (BY CONSTRUCTION - not a platform verdict)","model","S3",1),
]

print("=== STAGE 3 VERDICT GRID ===\n")
print(f"{'platform':14s} {'transition':11s} {'property':16s} {'reading':22s} {'verdict':10s} {'lvl':5s} {'sev':4s} {'CRD':>4s}")
for p,t,prop,rd,v,ev,lvl,sev,crd in R:
    print(f"{p:14s} {t:11s} {prop:16s} {rd:22s} {v:10s} {lvl:5s} {sev:4s} {str(crd):>4s}")

# --- CONT: cells where the property's truth FLIPS between readings ---
from collections import defaultdict
byc = defaultdict(set)
for p,t,prop,rd,v,ev,lvl,sev,crd in R:
    byc[(p,t,prop)].add(v)
cont = [k for k,vs in byc.items() if len(vs) > 1]
robust = [k for k,vs in byc.items() if len(vs)==1 and len([1 for r in R if (r[0],r[1],r[2])==k])>1]

print(f"\n=== DETERMINACY (Def. 5-6) ===")
print(f"  CONTINGENT cells (truth flips between readings): {len(cont)}")
for c in cont: print(f"    - {c[0]} / {c[1]} / {c[2]}")
print(f"  SILENT-ROBUST cells (silent but truth same both ways): {len(robust)}")
for c in robust: print(f"    - {c[0]} / {c[1]} / {c[2]}  <= silence is harmless here")
print(f"\n  CONT total = {len(cont)}    EXIT-B threshold = 8  ->  {'MET' if len(cont)>=8 else 'NOT MET'}")

# --- EXIT-A: >=1 cell with RRC>0, severity >=S3, CRD>=2, A5 PASS, DETERMINED, shipping ---
SEVRANK = {"S0":0,"S1":1,"S2":2,"S3":3,"S4":4,"S5":5}
exitA = [r for r in R if r[4]=="FALSIFIED" and SEVRANK[r[7]]>=3 and (r[8] or 0)>=2
         and "documented" in r[3] and r[0]!="*"]
print("\n=== EXIT-A CANDIDATES (severity>=S3 AND CRD>=2 AND DETERMINED AND shipping platform) ===")
for r in exitA: print(f"    {r[0]} / {r[1]} / {r[2]}  sev={r[7]} CRD={r[8]}  [{r[5]}]")
print(f"\n  A5 necessity + matched budget: PASS (E3.4/E3.5, empirical, CRD=2 confirmed)")
print(f"\n  >>> GATE VERDICT: {'EXIT-A' if exitA else ('EXIT-B' if len(cont)>=8 else 'EXIT-C')}")
print("\n  QUALIFICATIONS ON RECORD:")
print("   1. Def.4 clause (v) is not cleanly satisfied for the HA cell: the orphaned")
print("      socket holds a strong reference to the removed user's object. Nothing")
print("      HOUSEHOLD-ENUMERABLE names them (config/auth/list shows 3 not 4), but the")
print("      strict reading is arguable. Same nuance that demoted R1 to defect-class.")
print("   2. Coverage is PARTIAL: 4 properties probed, but not every (platform x")
print("      transition x property) combination. RC is well covered on `evict`;")
print("      NRT/GTB/DNA are probed platform-neutrally, not per-platform.")
print("   3. DNA-device FALSIFIED is BY CONSTRUCTION and is not a platform verdict.")
