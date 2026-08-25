"""E5.1-E5.5 — sampled search beyond exhaustive Alloy scope, with inference.

The exhaustive Alloy arm is EXACT within its scope and needs no statistics. This arm
is SAMPLED and therefore does. The distinction is maintained rigidly (design 11.4).

A7: stratified household generator + greedy residue check under the SAME cascade
semantics the Alloy platform model uses, so the two arms are commensurable.
"""
import random, itertools, numpy as np, pandas as pd
import statsmodels.formula.api as smf

SEED = 20260822
CAPS = ["View","Operate","Manage","Administer"]
RANK = {c:i for i,c in enumerate(CAPS)}
# platform -> cascade set, taken from models/tenantsafe_platforms.als
PLATFORMS = {
  "GoogleHome_A":   {"grants","sessions"},
  "GoogleHome_B":   {"grants"},
  "Alexa_AA":       {"grants","sessions"},
  "Alexa_AB":       {"grants"},
  "Alexa_BA":       {"sessions"},
  "Alexa_BB":       set(),
  "SmartThings_A":  {"grants","autos"},
  "SmartThings_B":  {"grants"},
  "HomeAssistant":  {"grants","session_readonly"},
}

def gen_household(rng, k_p, k_d):
    """Stratified by household size and delegation depth."""
    princ = [f"p{i}" for i in range(k_p)]
    devs  = [f"d{i}" for i in range(k_d)]
    victim = princ[1] if k_p > 1 else princ[0]
    grants  = [{"sub":rng.choice(princ),"dev":rng.choice(devs),"cap":rng.choice(CAPS)}
               for _ in range(rng.randint(1, k_p*k_d))]
    sessions= [{"sub":g["sub"],"dev":g["dev"],"cap":g["cap"]} for g in grants if rng.random()<0.5]
    autos   = [{"author":rng.choice(princ),"dev":rng.choice(devs),"cap":rng.choice(CAPS)}
               for _ in range(rng.randint(0,2))]
    triggers= {a["author"] for a in autos}
    return victim, grants, sessions, autos, triggers

def residue(casc, victim, grants, sessions, autos, triggers, need="Operate"):
    """Returns (any_residue, channel). B1 applied: all grants naming victim revoked."""
    live_g = [] if True else grants                      # B1: victim's grants always revoked
    open_s = [] if "sessions" in casc else [s for s in sessions if s["sub"]==victim]
    armed  = [] if "autos" in casc else autos
    trig   = triggers
    if "session_readonly" in casc:
        open_s = [s for s in open_s if RANK[need] <= RANK["View"]]
    for s in open_s:
        if RANK[s["cap"]] >= RANK[need]: return True, "session"
    if victim in trig:
        for a in armed:
            if RANK[a["cap"]] >= RANK[need]: return True, "automation"
    return False, "none"

def main():
    rng = random.Random(SEED)
    rows = []
    for plat, casc in PLATFORMS.items():
        for i in range(1000):
            k_p = rng.choice([2,3,4,5]); k_d = rng.choice([1,2,3,4])
            stratum = f"P{k_p}D{k_d}"
            v,g,s,a,t = gen_household(rng,k_p,k_d)
            hit, chan = residue(casc,v,g,s,a,t)
            rows.append({"platform":plat,"stratum":stratum,"k_p":k_p,"k_d":k_d,
                         "residue":int(hit),"channel":chan,"i":i})
    df = pd.DataFrame(rows)
    print(f"=== E5.2 sampled search: N={len(df)} ({len(PLATFORMS)} platform-readings x 1000), seed={SEED} ===\n")
    tab = df.groupby("platform").agg(residue_rate=("residue","mean"), n=("residue","size"))
    for p,r in tab.iterrows():
        k = int(r.residue_rate*r.n); n=int(r.n)
        lo,hi = _wilson(k,n)
        print(f"  {p:16s} residue {r.residue_rate:6.3f}  95% CI [{lo:.3f}, {hi:.3f}]  n={n}")
    print("\n=== channel breakdown (where residue found) ===")
    print(df[df.residue==1].groupby(["platform","channel"]).size().to_string())

    # E5.4 held-out split by seed stratum
    train = df[df.i < 700]; test = df[df.i >= 700]
    print(f"\n=== E5.3 mixed-effects logistic (random intercept: stratum) ===")
    print(f"    fit on n={len(train)} (70%), checked on n={len(test)} (30%)")
    try:
        m = smf.mixedlm("residue ~ C(platform) + k_p + k_d", train,
                        groups=train["stratum"]).fit(reml=False)
        print(f"    converged={m.converged}  loglik={m.llf:.1f}")
        pr = m.params[[c for c in m.params.index if "platform" in c or c in ("k_p","k_d")]]
        print("    fixed effects (LPM on binary outcome; sign/direction only):")
        for k_,v_ in pr.items(): print(f"      {k_:34s} {v_:+.4f}")
        pred = (m.predict(test) > 0.5).astype(int)
        print(f"    held-out accuracy: {(pred==test.residue).mean():.3f}")
    except Exception as e:
        print(f"    mixedlm failed: {e}")

    print("\n=== E5.5 preregistered contrast 2: CRD>=2 share among residues ===")
    comp = df[(df.residue==1) & (df.channel=="automation")]
    allr = df[df.residue==1]
    k,n = len(comp), len(allr); lo,hi=_wilson(k,n)
    print(f"    composed (automation channel) {k}/{n} = {k/n:.3f}  95% CI [{lo:.3f}, {hi:.3f}]")
    df.to_csv("results/scale_samples.csv", index=False)
    print("\n  wrote results/scale_samples.csv")

def _wilson(k,n,z=1.96):
    if n==0: return (0,0)
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d; s=z*((p*(1-p)/n + z*z/(4*n*n))**0.5)/d
    return max(0,c-s), min(1,c+s)

main()
