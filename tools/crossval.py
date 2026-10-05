#!/usr/bin/env python3
"""Emit the residue-finder vs Alloy cross-validation table.

The appendix asserts agreement on ten path-level comparisons. This produces the
comparison so a reader can audit it instead of taking the sentence on trust.
"""
import json, subprocess, sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
ALLOY = {  # Alloy command -> verdict, from results/scope_sweep/raw_S1.txt (scope S1)
 ("google_home","evict_readingA_sessions_terminate","operate_via_session"):("GHA_sess_act","UNSAT"),
 ("google_home","evict_readingA_sessions_terminate","operate_via_automation"):("GHA_auto_act","SAT"),
 ("google_home","evict_readingB_sessions_persist","operate_via_session"):("GHB_sess_act","SAT"),
 ("google_home","evict_readingB_sessions_persist","operate_via_automation"):("GHB_auto_act","SAT"),
 ("alexa","evict_AA_grants_and_sessions","operate_via_session"):("ALXAA_sess_act","UNSAT"),
 ("alexa","evict_AB_grants_only","operate_via_session"):("ALXAB_sess_act","SAT"),
 ("alexa","evict_BA_sessions_only","operate_via_session"):("ALXBA_sess_act","UNSAT"),
 ("alexa","evict_BB_neither","operate_via_session"):("ALXBB_sess_act","SAT"),
 ("smartthings","evict_readingA_routines_die","operate_via_automation"):("STA_auto_act","SAT"),
 ("smartthings","evict_readingB_routines_survive","operate_via_automation"):("STB_auto_act","SAT"),
}
rows=[]; agree=0
for spec in ("google_home","alexa","smartthings"):
    out=json.loads(subprocess.run(["python3",str(ROOT/"tools/residue_finder.py"),
        str(ROOT/f"tools/specs/{spec}.json"),"--json"],capture_output=True,text=True).stdout)
    for r in out:
        for f in r["findings"]:
            key=(spec,r["transition"],f["capability"])
            if key not in ALLOY: continue
            cmd,av=ALLOY[key]
            tool="residual" if f["residual"] else "clean"
            want="residual" if av=="SAT" else "clean"
            ok = tool==want; agree += ok
            rows.append((spec,r["transition"],f["capability"],tool,f.get("crd","--"),cmd,av,"yes" if ok else "NO"))
print(f"{'platform':13s} {'reading':34s} {'capability':24s} {'tool':9s} {'CRD':>3s} {'alloy cmd':18s} {'verdict':7s} agree")
for r in rows: print(f"{r[0]:13s} {r[1]:34s} {r[2]:24s} {r[3]:9s} {str(r[4]):>3s} {r[5]:18s} {r[6]:7s} {r[7]}")
print(f"\nagreement: {agree}/{len(rows)}")
json.dump(rows, open(ROOT/"results/crossval.json","w"), indent=1)
sys.exit(0 if agree==len(rows) else 1)
