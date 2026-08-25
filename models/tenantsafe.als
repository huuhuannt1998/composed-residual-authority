/*
  TENANTSAFE — M2 Stage 0, Alloy arm.

  TOOL RATIONALE (design section 5.0, justified on property structure not familiarity):
  revocation-completeness and no-residual-access-after-transfer are BOUNDED
  REACHABILITY over rich heterogeneous state (grants, sessions, automations,
  triggers). Alloy is counterexample-rich and fast there. Tamarin is retained
  for delegation-non-amplification, which is a safety invariant over UNBOUNDED
  delegation chains and needs induction that finite scope cannot supply.

  SCOPE JUSTIFICATION (design insight I5): every documented harm in the
  multi-user smart-home literature involves <= 5 principals and <= 4 devices.
  Jackson's small-scope hypothesis is unusually well-founded here because
  HOUSEHOLDS are small, so exhaustive analysis at this scope is adequate
  rather than a concession.

  STAGE 0 SCOPE: base model + executability (legitimate workflows must run).
  Property verdicts are Stage 3 and are NOT claimed here.
*/
module tenantsafe

abstract sig Cap {}
one sig View, Operate, Manage, Administer extends Cap {}

// held -> need : "holding `held` suffices for `need`"  (View < Operate < Manage < Administer)
fun dominates : Cap -> Cap {
    View->View + Operate->Operate + Manage->Manage + Administer->Administer
  + Operate->View
  + Manage->View + Manage->Operate
  + Administer->View + Administer->Operate + Administer->Manage
}

sig Principal {}
sig Device {}

// Immutable identity of the artifacts; their LIVENESS is the mutable part.
sig Grant   { g_iss: Principal, g_sub: Principal, g_dev: Device, g_cap: Cap }
sig Session { s_sub: Principal, s_dev: Device, s_cap: Cap, s_from: Grant }
sig Auto    { a_author: Principal, a_dev: Device, a_cap: Cap }

// Mutable state (Alloy 6 temporal). Mirrors the Tamarin linear/persistent split:
// membership, grant liveness, session openness and trigger binding are all revocable.
var sig Member  in Principal {}
var sig Evicted in Principal {}
var sig Live    in Grant     {}
var sig Open    in Session   {}
var sig Armed   in Auto      {}
var sig Trigger in Principal {}

one sig Owner in Principal {}

// A session is minted from a grant; an automation's author held a grant on its device.
fact wellFormed {
  all s: Session | s.s_from.g_sub = s.s_sub and s.s_from.g_dev = s.s_dev and s.s_cap = s.s_from.g_cap
  all g: Grant   | g.g_iss != g.g_sub
  Owner not in Evicted
}

/* ---------------------------------------------------------------- EFFECT (design A1)
   Three paths. The grant path checks CURRENT membership. The other two do not --
   that is the whole point, and it is where residue comes from. */

pred effectViaGrant[p: Principal, d: Device, c: Cap] {
  p in Member
  some g: Live | g.g_sub = p and g.g_dev = d and c in g.g_cap.dominates
}
pred effectViaSession[p: Principal, d: Device, c: Cap] {          // no membership check
  some s: Open | s.s_sub = p and s.s_dev = d and c in s.s_cap.dominates
}
pred effectViaAutomation[p: Principal, d: Device, c: Cap] {        // the deputy
  p in Trigger                                                     // p only TRIGGERS
  some a: Armed | a.a_dev = d and c in a.a_cap.dominates           // authority is the automation's
}
pred canEffect[p: Principal, d: Device, c: Cap] {
  effectViaGrant[p,d,c] or effectViaSession[p,d,c] or effectViaAutomation[p,d,c]
}

/* ------------------------------------------------------------------- transitions */

pred admit[p: Principal] {
  p not in Member and p not in Evicted
  Member' = Member + p
  Evicted' = Evicted and Live' = Live and Open' = Open and Armed' = Armed and Trigger' = Trigger
}
pred grant[g: Grant] {
  g not in Live and g.g_iss in Member and g.g_sub in Member
  Live' = Live + g
  Member' = Member and Evicted' = Evicted and Open' = Open and Armed' = Armed and Trigger' = Trigger
}
pred openSession[s: Session] {
  s not in Open and s.s_from in Live
  Open' = Open + s
  Member' = Member and Evicted' = Evicted and Live' = Live and Armed' = Armed and Trigger' = Trigger
}
pred arm[a: Auto] {
  a not in Armed and a.a_author in Member
  some g: Live | g.g_sub = a.a_author and g.g_dev = a.a_dev
  Armed' = Armed + a and Trigger' = Trigger + a.a_author
  Member' = Member and Evicted' = Evicted and Live' = Live and Open' = Open
}
// EVICT: consumes membership only. Exactly what platforms document.
pred evict[p: Principal] {
  p in Member and p != Owner
  Member' = Member - p and Evicted' = Evicted + p
  Live' = Live and Open' = Open and Armed' = Armed and Trigger' = Trigger
}
// BASELINE B1 -- the documented remediation: delete the ACL row naming the principal.
pred revokeGrant[g: Grant] {
  g in Live
  Live' = Live - g
  Member' = Member and Evicted' = Evicted and Open' = Open and Armed' = Armed and Trigger' = Trigger
}
// Remediations NO platform documents:
pred revokeSession[s: Session] {
  s in Open
  Open' = Open - s
  Member' = Member and Evicted' = Evicted and Live' = Live and Armed' = Armed and Trigger' = Trigger
}
pred disarm[a: Auto] {
  a in Armed
  Armed' = Armed - a
  Member' = Member and Evicted' = Evicted and Live' = Live and Open' = Open and Trigger' = Trigger
}
pred unbindTrigger[p: Principal] {
  p in Trigger
  Trigger' = Trigger - p
  Member' = Member and Evicted' = Evicted and Live' = Live and Open' = Open and Armed' = Armed
}
pred stutter {
  Member' = Member and Evicted' = Evicted and Live' = Live
  and Open' = Open and Armed' = Armed and Trigger' = Trigger
}

fact init {
  Member = Owner and no Evicted and no Live and no Open and no Armed and no Trigger
}
fact transitions {
  always (
       stutter
    or (some p: Principal | admit[p] or evict[p] or unbindTrigger[p])
    or (some g: Grant   | grant[g] or revokeGrant[g])
    or (some s: Session | openSession[s] or revokeSession[s])
    or (some a: Auto    | arm[a] or disarm[a])
  )
}

/* ============================================================================
   STAGE 0 — EXECUTABILITY. Every legitimate workflow must run, or every
   property proves vacuously (design mitigation C3).
   ============================================================================ */

run exec_onboard_and_act {
  some p: Principal, d: Device |
    eventually (p in Member and canEffect[p, d, Operate])
} for 4 but 3 Principal, 2 Device, 3 Grant, 2 Session, 2 Auto, 8 steps

run exec_author_automation {
  some a: Auto | eventually (a in Armed)
} for 4 but 3 Principal, 2 Device, 3 Grant, 2 Session, 2 Auto, 8 steps

run exec_evict_runs {
  some p: Principal | eventually (p in Evicted)
} for 4 but 3 Principal, 2 Device, 3 Grant, 2 Session, 2 Auto, 8 steps

run exec_full_remediation {
  some p: Principal | eventually (p in Evicted and (no g: Live | g.g_sub = p))
} for 4 but 3 Principal, 2 Device, 3 Grant, 2 Session, 2 Auto, 8 steps
