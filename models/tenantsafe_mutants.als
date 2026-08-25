/*
  P0 EXPERIMENT 2 — MODEL MUTATION TESTING.

  A model that reproduces one known trace proves nothing: it may have been
  tailored to that trace. This suite mutates the revocation semantics and asks
  whether the model returns a DIFFERENT verdict for each mutant. An instrument
  that reports "residue" for correct cascading revocation, or that reports
  depth 2 for an ordinary forgotten ACL row, is not measuring what we claim.

  Each mutant fixes a survivor set Surv (what the transition failed to remove).
  For each we ask three questions and derive the verdict mechanically:

      actuate_full    Avail = Surv, is Actuate induced?          -> residue?
      actuate_single  some singleton in Surv induces Actuate?    -> depth 1?
      audit_clean     Grant not in Surv                          -> does any
                                                                    surviving
                                                                    object name p?
      CRD  = 1 if actuate_single SAT; 2 if UNSAT but full SAT; undefined if none
      CRA  = residue AND CRD >= 2 AND audit_clean

  Chains are inherited verbatim from tenantsafe_crd.als; nothing about the
  induced-effect relation is re-tuned per mutant. Only Surv changes.
*/
module tenantsafe_mutants

abstract sig Carrier {}
one sig Session    extends Carrier {}   // orphaned authenticated socket
one sig Automation extends Carrier {}   // event-triggered household automation
one sig Grant      extends Carrier {}   // an ACL row naming the principal
one sig Binding    extends Carrier {}   // secondary-ecosystem binding
one sig GuestGrant extends Carrier {}   // a guest grant PAST its expiry

abstract sig Cap {}
one sig Read, Actuate extends Cap {}

sig Avail in Carrier {}

/* Chains, identical to the CRD model. Note GuestGrant appears in NO chain:
   an expired grant confers no authority. That is the property M3 tests. */
pred chainSessionRead { Session in Avail }
pred chainDeputy      { Session in Avail and Automation in Avail }
pred chainGrant       { Grant in Avail }
pred chainBinding     { Binding in Avail }

pred induces[c: Cap] {
  c = Read    implies (chainSessionRead or chainGrant or chainBinding or chainDeputy)
  c = Actuate implies (chainDeputy or chainGrant or chainBinding)
}

/* ============ M1. Forgotten grant row: p remains explicitly authorized ====== */
run M1_actuate_full   { Avail = Grant and induces[Actuate] } for 5
run M1_actuate_single { some c: Carrier | c in Grant and Avail = c and induces[Actuate] } for 5

/* ============ M2. Surviving session only, no deputy ======================== */
run M2_read_full      { Avail = Session and induces[Read] } for 5
run M2_actuate_full   { Avail = Session and induces[Actuate] } for 5

/* ============ M3. Guest grant PAST EXPIRY plus a surviving session ========= */
run M3_read_full      { Avail = Session + GuestGrant and induces[Read] } for 5
run M3_actuate_full   { Avail = Session + GuestGrant and induces[Actuate] } for 5
// the expired grant must contribute nothing on its own:
run M3_expired_alone  { Avail = GuestGrant and (induces[Read] or induces[Actuate]) } for 5

/* ============ M4. Secondary ecosystem binding survives local removal ======= */
run M4_actuate_full   { Avail = Binding and induces[Actuate] } for 5
run M4_actuate_single { some c: Carrier | c in Binding and Avail = c and induces[Actuate] } for 5

/* ============ M5. Session + automation composition (the HA witness) ======== */
run M5_actuate_full   { Avail = Session + Automation and induces[Actuate] } for 5
run M5_actuate_single { some c: Carrier | c in (Session + Automation) and Avail = c and induces[Actuate] } for 5

/* ============ M6. CORRECT cascading revocation: nothing survives =========== */
run M6_residue_any    { Avail = none and (induces[Read] or induces[Actuate]) } for 5

/* ============ M7. Broken cascade: only the ACL row was removed ============= */
run M7_actuate_full   { Avail = Session + Automation + Binding and induces[Actuate] } for 5
run M7_actuate_single { some c: Carrier | c in (Session + Automation + Binding) and Avail = c and induces[Actuate] } for 5

/* ============ M8. Direct unauthorized service call after removal =========== */
// With only the orphaned session and no deputy, direct actuation must be denied.
check M8_direct_call_denied { Avail = Session implies not induces[Actuate] } for 5
