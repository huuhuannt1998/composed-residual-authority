/*
  P2 EXPERIMENT 18 - depth > 2 synthetic validation.

  A sceptic can read "composition depth 2" as a renaming of "two things had to
  survive", in which case the definition carries no content beyond a conjunction
  and would never yield 3. This file constructs synthetic instances at depth 1,
  2 and 3 under the SAME definition of minimal sufficient support used for the
  Home Assistant witness, and checks each one exactly:

      CRD(c) = min |S| over supports S that are sufficient for c

  For each depth d we assert BOTH directions, which is what makes the check
  meaningful rather than decorative:
      (a) some support of size d IS sufficient          -> run, expect SAT
      (b) NO support of size < d is sufficient          -> check, expect UNSAT
  A definition that collapsed to "two objects" would fail (b) at d = 3.

  The depth-3 chain is the review's example: stale session -> external trigger
  entity -> local automation -> secondary binding -> effect. The session and the
  automation alone cannot reach the device because the device lives in the
  SECOND ecosystem, whose dispatch requires the binding.
*/
module tenantsafe_depth

abstract sig Carrier {}
one sig Session   extends Carrier {}   // orphaned authenticated socket
one sig Trigger   extends Carrier {}   // external trigger entity the session can set
one sig Automation extends Carrier {}  // local automation armed on that entity
one sig Binding   extends Carrier {}   // surviving secondary-ecosystem binding
one sig Grant     extends Carrier {}   // an ACL row naming the principal

abstract sig Cap {}
one sig LocalRead, LocalAct, RemoteAct, RelayAct extends Cap {}

sig Avail in Carrier {}

/* ---- chains. Each conjunct is a carrier that must be present. ------------- */

// depth 1: a surviving ACL row is sufficient on its own.
pred c_grant { Grant in Avail }

// depth 1: the orphaned socket reads local state on its own.
pred c_read  { Session in Avail }

// depth 2: session emits, local automation converts to a LOCAL device effect.
pred c_local { Session in Avail and Automation in Avail }

// depth 3: session emits, the local automation converts it to a service call,
// and the SECOND ecosystem's binding dispatches it. Exactly three carriers, and
// no two of them suffice.
pred c_relay { Session in Avail and Automation in Avail and Binding in Avail }

// depth 4: session sets an external trigger entity, the automation fires on it,
// and the resulting call is dispatched into the SECOND ecosystem, which only the
// surviving binding can reach. No two of these three suffice.
pred c_remote { Session in Avail and Trigger in Avail and Automation in Avail and Binding in Avail }

pred induces[c: Cap] {
  c = LocalRead  implies (c_read or c_grant)
  c = LocalAct   implies (c_local or c_grant)
  c = RemoteAct  implies c_remote
  c = RelayAct   implies c_relay
}

pred sufficientFor[S: set Carrier, c: Cap] { Avail = S and induces[c] }

/* ---- no ACL row survives: the audit is clean in every case below ---------- */
pred auditClean { Grant not in Avail }

/* ====================== DEPTH 1 ============================================ */
run D1_size1_sufficient  { Avail = Session and induces[LocalRead] } for 5
check D1_no_smaller {                       // nothing smaller than 1 works
  no S: set Carrier | #S < 1 and sufficientFor[S, LocalRead]
} for 5

/* ====================== DEPTH 2 ============================================ */
run D2_size2_sufficient  { auditClean and Avail = Session + Automation and induces[LocalAct] } for 5
check D2_no_smaller {
  no S: set Carrier | auditClean and #S < 2 and sufficientFor[S, LocalAct]
} for 5

/* ====================== DEPTH 3 (exactly three carriers) =================== */
run D3_size3_sufficient { auditClean and Avail = Session + Automation + Binding and induces[RelayAct] } for 5
check D3_no_smaller_than_3 {
  no S: set Carrier | auditClean and #S < 3 and sufficientFor[S, RelayAct]
} for 5
run D3_pair_session_automation { auditClean and Avail = Session + Automation and induces[RelayAct] } for 5
run D3_pair_session_binding    { auditClean and Avail = Session + Binding    and induces[RelayAct] } for 5

/* ====================== DEPTH 4 (the review's example chain) =============== */
// (a) a support of size 4 containing the chain is sufficient...
run D4_chain_sufficient {
  auditClean and Avail = Session + Trigger + Automation + Binding and induces[RemoteAct]
} for 5
// (b) ...and NOTHING of size < 4 is. This is the load-bearing check: if the
// definition were merely "two objects", this would be SAT.
check D4_no_smaller {
  no S: set Carrier | auditClean and #S < 4 and sufficientFor[S, RemoteAct]
} for 5
// (c) the specific two- and three-object subsets a sceptic would propose:
run D4_session_automation_only { auditClean and Avail = Session + Automation and induces[RemoteAct] } for 5
run D4_no_binding             { auditClean and Avail = Session + Trigger + Automation and induces[RemoteAct] } for 5
run D4_no_trigger             { auditClean and Avail = Session + Automation + Binding and induces[RemoteAct] } for 5

/* ====================== SEPARATION ========================================= */
// The three depths are genuinely different: the depth-2 support does NOT reach
// the depth-3 capability, so depth is a property of the capability, not a label.
check depths_are_distinct {
  no S: set Carrier | auditClean and #S = 2 and sufficientFor[S, RemoteAct]
} for 5
