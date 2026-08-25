/*
  P0 REPAIR — composition depth as MINIMAL SUFFICIENT SUPPORT.

  The earlier definition took CRD as the size of a minimal REMOVAL CUT: a minimal
  set whose deletion destroys the residue. That is wrong for the intended claim.
  In the Home Assistant witness, deleting the session alone destroys the effect and
  deleting the automation alone destroys the effect, so {session} and {automation}
  are each minimal cuts of size one, giving CRD = 1 and falsifying the depth >= 2
  condition that Composed Residual Authority requires.

  The repaired definition asks which objects must be PRESENT TOGETHER for the effect
  to be reachable at all:

      S is sufficient  iff  the effect is reachable when only S is available
      S is minimal     iff  no proper subset of S is sufficient
      CRD              =    min |S| over minimal sufficient supports

  Cut-minimality and support-minimality coincide only when the carriers are
  independent. They diverge exactly in the composed case, which is the case of
  interest, so the distinction is load-bearing rather than pedantic.

  This file also encodes the INDUCED-effect relation. The removed principal never
  performs the service call; the automation does. Following the review's Option C,
  induction is an authority-carrier chain, each step permitted by the system:
      principal -> surviving session -> event -> armed automation -> service call.
*/
module tenantsafe_crd

abstract sig Carrier {}          // surviving authority-relevant objects
one sig Session   extends Carrier {}   // orphaned authenticated socket
one sig Automation extends Carrier {}  // event-triggered household automation
one sig Grant     extends Carrier {}   // an ACL row naming the principal
one sig Binding   extends Carrier {}   // secondary-ecosystem binding

abstract sig Cap {}
one sig Read, Actuate extends Cap {}

/* ---- which carriers survive the transition, per platform semantics ---------
   `Avail` is the support under test: exactly the carriers made available. */
sig Avail in Carrier {}

/* ---- the induced-effect relation (review section 8, Option C) --------------
   Each disjunct is one complete authority-carrier chain. A chain is available
   only if every carrier it traverses is in the support. */

// Chain 1: session alone. After removal the socket reads but cannot actuate,
// which is the measured Home Assistant behaviour.
pred chainSessionRead  { Session in Avail }

// Chain 2: the deputy. The principal fires an event through the surviving
// session; an armed automation receives it and performs the service call under
// its own context. BOTH carriers are required: the session to emit the event,
// the automation to convert it into a device effect.
pred chainDeputy { Session in Avail and Automation in Avail }

// Chain 3: a surviving ACL row naming the principal - the ordinary,
// non-composed residue that a depth-1 defect produces.
pred chainGrant { Grant in Avail }

// Chain 4: a second ecosystem dispatches independently.
pred chainBinding { Binding in Avail }

pred induces[c: Cap] {
  c = Read    implies (chainSessionRead or chainGrant or chainBinding or chainDeputy)
  c = Actuate implies (chainDeputy or chainGrant or chainBinding)
}

/* ---- sufficiency and minimality ------------------------------------------- */
pred sufficientFor[S: set Carrier, c: Cap] { Avail = S and induces[c] }

/* ---- the Home Assistant platform instance ---------------------------------
   Removal cascades ACL rows (so Grant does not survive) and there is no second
   ecosystem. Session and Automation survive; this is the configuration the
   runtime experiment exercised. */
pred HA_survivors { Grant not in Avail and Binding not in Avail }

/* =========================== CHECKS ======================================== */

// R1. The pair {Session, Automation} IS sufficient for actuation.
run R1_pair_sufficient {
  HA_survivors and Avail = Session + Automation and induces[Actuate]
} for 4

// R2. Neither singleton is sufficient for actuation. Both must be UNSAT.
run R2a_session_alone_actuates { HA_survivors and Avail = Session   and induces[Actuate] } for 4
run R2b_automation_alone_actuates { HA_survivors and Avail = Automation and induces[Actuate] } for 4

// R3. THE REPAIRED CLAIM. Under HA survivor semantics, no support of size < 2
// is sufficient for actuation, so the minimal sufficient support has size 2.
// UNSAT is the required outcome.
check R3_no_smaller_sufficient_support {
  no S: set Carrier |
    HA_survivors and #S < 2 and sufficientFor[S, Actuate]
} for 4

// R4. Read is reachable from the session alone, so the READ residue is depth 1
// while the ACTUATION residue is depth 2. The two must not be conflated.
run R4_read_is_depth_one { HA_survivors and Avail = Session and induces[Read] } for 4

// R5. Sanity: with a surviving ACL row the residue is ordinary depth-1, which is
// the defect class the paper explicitly does NOT claim as composed.
run R5_grant_is_depth_one { Avail = Grant and induces[Actuate] } for 4
