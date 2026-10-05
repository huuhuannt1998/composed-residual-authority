#!/usr/bin/env python3
"""residue_finder - find residual authority from a platform transition spec.

Consumes a declarative spec of a platform's transition semantics and reports,
for every capability the policy denies after the transition, whether it is still
INDUCED, and if so the witness chain, the minimal sufficient support, the
composition depth, and which of the surviving objects are visible to an auditor.

The search is exhaustive over subsets of the surviving carrier set, so within a
spec the result is exact, not a heuristic. Complexity is 2^|carriers| and the
carrier sets that describe real platform transitions are small (<= 8 here).

  usage:  residue_finder.py <spec.json> [--platform NAME] [--json]

Spec shape:
  {
    "platform": "...",
    "carriers": {"name": {"audit_visible": bool, "names_principal": bool}},
    "capabilities": ["read", "actuate", ...],
    "chains": [{"cap": "...", "requires": [carrier...], "trace": [step...]}],
    "transitions": {"evict": {"removes": [carrier...], "denies": [cap...]}}
  }
A chain is available exactly when every carrier it requires has survived.
"""
import itertools, json, sys

def induced(cap, support, chains):
    """Every chain for `cap` whose required carriers are all in `support`."""
    return [c for c in chains if c["cap"] == cap and set(c["requires"]) <= set(support)]

def minimal_supports(cap, survivors, chains):
    """All minimal S subset of survivors with S sufficient for cap.

    Minimal means no proper subset of S is sufficient.  Searching by ascending
    size and rejecting any S that contains an already-found sufficient set gives
    exactly the minimal ones."""
    found = []
    for k in range(0, len(survivors) + 1):
        for S in itertools.combinations(sorted(survivors), k):
            if any(set(f) < set(S) or set(f) == set(S) for f in found):
                continue
            if induced(cap, S, chains):
                found.append(S)
    return found

def analyse(spec, transition):
    t = spec["transitions"][transition]
    carriers = spec["carriers"]
    survivors = [c for c in carriers if c not in t["removes"]]
    out = {"platform": spec["platform"], "transition": transition,
           "survivors": survivors, "findings": []}
    for cap in t["denies"]:
        sups = minimal_supports(cap, survivors, spec["chains"])
        if not sups:
            out["findings"].append({"capability": cap, "residual": False}); continue
        crd = min(len(s) for s in sups)
        best = [s for s in sups if len(s) == crd]
        wit = induced(cap, best[0], spec["chains"])[0]
        # an auditor sees only objects the authorization state exposes; a residue
        # is HIDDEN when no surviving object in the support names the principal
        names = [c for c in best[0] if carriers[c].get("names_principal")]
        visible = [c for c in best[0] if carriers[c].get("audit_visible")]
        out["findings"].append({
            "capability": cap, "residual": True,
            "witness": wit["trace"], "minimal_support": list(best[0]),
            "all_minimal_supports": [list(s) for s in sups], "crd": crd,
            "audit_visible_objects": visible,
            "objects_naming_principal": names,
            "composed": crd >= 2,
            "hidden": len(names) == 0,
        })
    return out

def render(r):
    L = [f"Transition: {r['transition']}({r['platform']})",
         f"Survivors:  {{{', '.join(r['survivors'])}}}"]
    any_res = False
    for f in r["findings"]:
        if not f["residual"]:
            L.append(f"\n  {f['capability']}: no residual capability"); continue
        any_res = True
        L.append(f"\nResidual capability: {f['capability']}")
        L.append("Witness:")
        for i, s in enumerate(f["witness"]):
            L.append(("  " if i == 0 else "  -> ") + s)
        L.append(f"\nMinimal support:\n  {{{', '.join(f['minimal_support'])}}}")
        if len(f["all_minimal_supports"]) > 1:
            others = [s for s in f["all_minimal_supports"] if s != f["minimal_support"]]
            L.append(f"  (also minimal: {'; '.join('{'+', '.join(s)+'}' for s in others)})")
        L.append(f"\nCRD:\n  {f['crd']}" + ("   [composed]" if f["composed"] else "   [ordinary, depth 1]"))
        L.append(f"\nAudit-visible objects in support:\n  {'{'+', '.join(f['audit_visible_objects'])+'}' if f['audit_visible_objects'] else '  (none)'}")
        L.append(f"Objects naming the principal:\n  {'{'+', '.join(f['objects_naming_principal'])+'}' if f['objects_naming_principal'] else '  (none)  -> HIDDEN residue'}")
    if not any_res: L.append("\n  revocation complete: no denied capability remains induced")
    return "\n".join(L)

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    spec = json.load(open(args[0]))
    want = args[1] if len(args) > 1 else None
    reports = [analyse(spec, t) for t in spec["transitions"] if want in (None, t)]
    if "--json" in sys.argv:
        print(json.dumps(reports, indent=1))
    else:
        for r in reports: print(render(r)); print("\n" + "=" * 68)
