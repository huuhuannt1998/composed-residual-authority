/*
  TENANTSAFE — E4.5 (GTB, guest-time-bounding) and E2.10 (NRT, transfer, both directions).

  DEVIATION FROM DESIGN §5.0, RECORDED. The design assigned GTB to TLA+/TLC because
  Tamarin's ordering is too weak for real-time bounds. TLC is installed and works, but
  GTB is modelled HERE in Alloy instead. Reason, and it is the same argument that
  narrowed the Tamarin arm: a separate TLA+ spec would model a DIFFERENT system from
  the Alloy platform model, reintroducing exactly the cross-encoding conformance
  problem that made C7 inapplicable. Alloy 6 handles a bounded discrete clock
  adequately, and keeping GTB on the existing substrate means the timed property is
  checked against the SAME semantics as RC and NRT. Cost: no dense-time reasoning.
  That is acceptable because every documented guest window is discrete (schedules,
  hours, days).
*/
module tenantsafe_time_transfer

abstract sig Cap {}
one sig View, Operate, Manage, Administer extends Cap {}
fun dominates : Cap -> Cap {
    View->View + Operate->Operate + Manage->Manage + Administer->Administer
  + Operate->View + Manage->View + Manage->Operate
  + Administer->View + Administer->Operate + Administer->Manage }

sig Principal {}
sig Device {}
sig Grant { g_sub: Principal, g_dev: Device, g_cap: Cap, g_end: Int }   // g_end = expiry epoch
sig Session { s_sub: Principal, s_dev: Device, s_cap: Cap, s_from: Grant, s_life: Int }

var one sig Clock { var now: Int }
var sig Member  in Principal {}
var sig Evicted in Principal {}
var sig Live    in Grant   {}
var sig Open    in Session {}
var sig OpenedAt in Session {}          // sessions that have been opened (for lifetime calc)
var sig History in Principal {}          // principals whose prior-owner data is still stored
one sig Owner in Principal {}

abstract sig Flag {}
one sig CascSessions, WipeHistory, ExpireCascadesSession extends Flag {}
sig Cascades in Flag {}

fact wf {
  all s: Session | s.s_from.g_sub = s.s_sub and s.s_from.g_dev = s.s_dev and s.s_cap = s.s_from.g_cap
  all g: Grant | g.g_end >= 0 and g.g_end <= 6
  all s: Session | s.s_life >= 0 and s.s_life <= 6
  always (Cascades' = Cascades)
}

/* ---- GTB: a grant is EXPIRED once the clock passes its end epoch ---------- */
pred expired[g: Grant] { Clock.now > g.g_end }

pred canEffect[p: Principal, d: Device, c: Cap] {
  (some g: Live | g.g_sub = p and g.g_dev = d and c in g.g_cap.dominates and not expired[g])
  or (some s: Open | s.s_sub = p and s.s_dev = d and c in s.s_cap.dominates)
}

pred tick {
  // GUARD: Alloy Int is bitwidth-bounded; without this the clock wraps negative and
  // `expired` silently stops firing, which manufactured spurious SAT results.
  Clock.now < 6
  Clock.now' = Clock.now.plus[1]
  // expiry consumes the grant; whether it also kills the session it minted is the question
  Live' = Live - { g: Grant | Clock.now.plus[1] > g.g_end }
  (ExpireCascadesSession in Cascades)
     implies Open' = Open - { s: Session | Clock.now.plus[1] > s.s_from.g_end }
     else    Open' = Open
  Member'=Member and Evicted'=Evicted and OpenedAt'=OpenedAt and History'=History
}
pred admit[p: Principal] { p not in Member and p not in Evicted
  Member'=Member+p and Clock.now'=Clock.now and Evicted'=Evicted and Live'=Live and Open'=Open and OpenedAt'=OpenedAt and History'=History }
pred grant[g: Grant] { g not in Live and g.g_sub in Member and not expired[g]
  Live'=Live+g and Clock.now'=Clock.now and Member'=Member and Evicted'=Evicted and Open'=Open and OpenedAt'=OpenedAt and History'=History }
pred openSession[s: Session] { s not in Open and s.s_from in Live and s.s_sub in Member
  Open'=Open+s and OpenedAt'=OpenedAt+s and Clock.now'=Clock.now and Member'=Member and Evicted'=Evicted and Live'=Live and History'=History }
// TRANSFER: prior owner loses membership; new owner gains it. History wipe is optional.
// BUGFIX: old = new was permitted, which made 'transfer' a no-op that still marked the
// principal Evicted while leaving them a Member who could be re-granted.
pred transfer[old, new: Principal] { old != new and old in Member and new not in Member
  Member' = Member - old + new
  Evicted' = Evicted + old
  Live' = Live - { g: Grant | g.g_sub = old }
  (CascSessions in Cascades) implies Open' = Open - { s: Session | s.s_sub = old } else Open' = Open
  (WipeHistory in Cascades)  implies History' = History - old                      else History' = History + old
  Clock.now'=Clock.now and OpenedAt'=OpenedAt }
pred stutter { Clock.now'=Clock.now and Member'=Member and Evicted'=Evicted and Live'=Live and Open'=Open and OpenedAt'=OpenedAt and History'=History }

fact init { Clock.now = 0 and Member = Owner and no Evicted and no Live and no Open and no OpenedAt and no History }
fact trans { always ( stutter or tick
  or (some p: Principal | admit[p])
  or (some g: Grant | grant[g])
  or (some s: Session | openSession[s])
  or (some o, n: Principal | transfer[o, n]) ) }

/* ---- GTB: does a time-limited grant actually extinguish? ------------------ */
// TTE > 0 : the principal still effects the capability AFTER the grant's end epoch.
// GTB, stated precisely. TTE > 0 iff a session MINTED BY grant g is still open after
// g has expired. Earlier formulations were satisfiable via an unrelated still-valid
// grant or its session, which is not a GTB violation at all -- two successive bugs of
// the same class, both caught by a control that should have been UNSAT and was not.
pred gtb_violated { eventually (some s: Open | expired[s.s_from]) }

// Platform readings on whether expiry cascades to the session it minted.
pred R_expire_cascades     { Cascades = ExpireCascadesSession }
pred R_expire_no_cascade   { Cascades = none }

run GTB_holds_when_expiry_cascades { R_expire_cascades   and gtb_violated } for 4 but 3 Principal, 2 Device, 3 Grant, 2 Session, 10 steps, 5 Int
run GTB_fails_when_no_cascade      { R_expire_no_cascade and gtb_violated } for 4 but 3 Principal, 2 Device, 3 Grant, 2 Session, 10 steps, 5 Int

/* ---- NRT: no-residual-access-after-transfer, BOTH directions ------------- */
// Direction A: prior owner retains effect after transfer.
pred nrt_priorOwner { some o: Principal, d: Device, c: Cap |
  eventually (o in Evicted and o not in Member and canEffect[o, d, c]) }
// Direction B: new owner can read prior-owner state that was never wiped.
pred nrt_newOwnerReadsHistory { some o: Principal |
  eventually (o in Evicted and o in History) }

pred P_transfer_wipes    { Cascades = CascSessions + WipeHistory }
pred P_transfer_no_wipe  { Cascades = none }

run NRT_A_priorOwner_wipes    { P_transfer_wipes   and nrt_priorOwner } for 4 but 3 Principal, 2 Device, 3 Grant, 2 Session, 10 steps, 5 Int
run NRT_A_priorOwner_no_wipe  { P_transfer_no_wipe and nrt_priorOwner } for 4 but 3 Principal, 2 Device, 3 Grant, 2 Session, 10 steps, 5 Int
run NRT_B_history_wipes       { P_transfer_wipes   and nrt_newOwnerReadsHistory } for 4 but 3 Principal, 2 Device, 3 Grant, 2 Session, 10 steps, 5 Int
run NRT_B_history_no_wipe     { P_transfer_no_wipe and nrt_newOwnerReadsHistory } for 4 but 3 Principal, 2 Device, 3 Grant, 2 Session, 10 steps, 5 Int
