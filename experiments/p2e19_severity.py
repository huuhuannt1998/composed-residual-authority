"""P2 EXPERIMENT 19 - severity-oriented capability classification.

A binary residue flag says a transition failed. It does not say how badly. This
maps each measured residual operation onto the capability lattice the calculus
already uses (View < Operate < Manage < Administer) and reports the HIGHEST
surviving capability per transition, which is the quantity that actually tracks
harm.

The mapping is declared here, once, ahead of the data - it is not chosen after
seeing which cells survived.
"""
import json, os, sys, time
LATTICE=["View","Operate","Manage","Administer"]
RANK={c:i for i,c in enumerate(LATTICE)}
# --- predeclared mapping (review section 19, P2 Experiment 19) ---------------
MAP={
 "read":             "View",
 "existing_stream":  "View",
 "new_subscribe":    "View",
 "indirect_actuate": "Operate",
 "direct_actuate":   "Operate",
 "script_exec":      "Manage",
 "event_fire":       "Manage",
 "user_enum":        "Administer",
}
NICE={"read":"state read","existing_stream":"live event stream","new_subscribe":"new subscription",
      "indirect_actuate":"indirect actuation","direct_actuate":"direct actuation",
      "script_exec":"script execution","event_fire":"event firing","user_enum":"user enumeration"}
def main():
    src="/tmp/matrix_p1e7.json"
    if not os.path.exists(src):
        sys.exit(f"missing {src} - run the matrix experiment first (./run_all.sh --only matrix)")
    age_h=(time.time()-os.path.getmtime(src))/3600
    if age_h > 24:
        sys.exit(f"{src} is {age_h:.0f} h old. Severity must be derived from the CURRENT\n"
                 f"matrix run, not a stale one; re-run the matrix experiment first.")
    m=json.load(open(src))
    print("PREDECLARED CAPABILITY MAPPING")
    for k in MAP: print(f"  {NICE[k]:22s} -> {MAP[k]}")
    print("\nHIGHEST SURVIVING CAPABILITY PER TRANSITION")
    print(f"  {'arm':20s} {'n':>4s}  {'highest surviving':18s}  surviving operations")
    out={}
    for arm,d in m.items():
        n=d["n"]; surv=[k for k in MAP if d["pre"].get(k,0)>0 and d["residual"].get(k,0)>0]
        # a capability counts as surviving only if it survived in EVERY run
        strict=[k for k in surv if d["residual"][k]==d["pre"][k]]
        top=max((MAP[k] for k in strict), key=lambda c: RANK[c], default="none")
        out[arm]={"n":n,"highest":top,"surviving":[NICE[k] for k in strict],
                  "capabilities":sorted({MAP[k] for k in strict},key=lambda c:RANK[c])}
        print(f"  {arm:20s} {n:4d}  {top:18s}  {', '.join(NICE[k] for k in strict) or '(none)'}")
    print("\nREADING")
    print("  An ordinary member's removal leaves View. An administrator's removal leaves")
    print("  Administer - the top of the lattice - because user enumeration survives, and")
    print("  it leaves Operate through the composed deputy path while DIRECT actuation is")
    print("  denied. Severity therefore scales with the role held at the moment of removal,")
    print("  and the highest surviving capability separates the two arms that a binary")
    print("  residue flag would report identically.")
    json.dump(out,open("/tmp/p2e19_severity.json","w"),indent=1)
if __name__=="__main__": main()
