/*
  TENANTSAFE — M2 / T5. Per-platform instantiation from the M1 harvest.

  Each platform differs ONLY in what its `evict` transition CASCADES to. That is
  the whole content of the harvest expressed formally: eviction always ends
  membership; platforms differ in which OTHER surviving objects it takes with it.

  Cascade semantics are sourced from m1_jobb_semantics_harvest.md. Where
  documentation is SILENT, BOTH readings are instantiated and run (design A6),
  because picking one would manufacture a verdict the documentation does not support.

  STATUS: this is Stage 2 instantiation plus a STRUCTURAL residue probe.
  It is NOT the Stage 3 gate. The gate additionally requires the amended C7
  conformance fragment and the resolved severity catalog
  (chk_01M0HJVVM365YSPTQTT5S0HQJE). No EXIT verdict is claimed from this file.
*/
module tenantsafe_platforms

abstract sig Cap {}
one sig View, Operate, Manage, Administer extends Cap {}
fun dominates : Cap -> Cap {
    View->View + Operate->Operate + Manage->Manage + Administer->Administer
  + Operate->View + Manage->View + Manage->Operate
  + Administer->View + Administer->Operate + Administer->Manage
}

sig Principal {}
sig Device {}
sig Grant   { g_iss: Principal, g_sub: Principal, g_dev: Device, g_cap: Cap }
sig Session { s_sub: Principal, s_dev: Device, s_cap: Cap, s_from: Grant }
sig Auto    { a_author: Principal, a_dev: Device, a_cap: Cap }

var sig Member  in Principal {}
var sig Evicted in Principal {}
var sig Live    in Grant     {}
var sig Open    in Session   {}
var sig Armed   in Auto      {}
var sig Trigger in Principal {}
one sig Owner in Principal {}

/* ---- platform cascade configuration ------------------------------------- */
abstract sig Flag {}
one sig CascGrants, CascSessions, CascAutos, CascTriggers, SessReadOnly extends Flag {}
sig Cascades in Flag {}          // fixed per run by a platform predicate

fact wellFormed {
  all s: Session | s.s_from.g_sub = s.s_sub and s.s_from.g_dev = s.s_dev and s.s_cap = s.s_from.g_cap
  all g: Grant | g.g_iss != g.g_sub
  Owner not in Evicted
  always (Cascades' = Cascades)          // platform semantics do not change mid-trace
}

/* ---- EFFECT (design A1) --------------------------------------------------- */
pred effectViaGrant[p: Principal, d: Device, c: Cap] {
  p in Member
  some g: Live | g.g_sub = p and g.g_dev = d and c in g.g_cap.dominates
}
// SessReadOnly models Home Assistant precisely: after removal the orphaned socket
// still READS (confirmed at L3, jrn_01M0HJTVJJM5W7JR52KGVGN3DW) but cannot actuate,
// because service calls re-resolve the user by ID while reads trust the stale object.
pred effectViaSession[p: Principal, d: Device, c: Cap] {
  some s: Open | s.s_sub = p and s.s_dev = d and
    ( (SessReadOnly in Cascades and p in Evicted) implies c = View
                                                  else c in s.s_cap.dominates )
}
pred effectViaAutomation[p: Principal, d: Device, c: Cap] {
  p in Trigger
  some a: Armed | a.a_dev = d and c in a.a_cap.dominates
}
pred canEffect[p: Principal, d: Device, c: Cap] {
  effectViaGrant[p,d,c] or effectViaSession[p,d,c] or effectViaAutomation[p,d,c]
}

/* ---- transitions ---------------------------------------------------------- */
pred admit[p: Principal] {
  p not in Member and p not in Evicted
  Member' = Member + p
  Evicted'=Evicted and Live'=Live and Open'=Open and Armed'=Armed and Trigger'=Trigger
}
pred grant[g: Grant] {
  g not in Live and g.g_iss in Member and g.g_sub in Member
  Live' = Live + g
  Member'=Member and Evicted'=Evicted and Open'=Open and Armed'=Armed and Trigger'=Trigger
}
pred openSession[s: Session] {
  // FAITHFULNESS FIX (2026-08-22): a session can only be MINTED for a current member.
  // Without this guard the model allowed a session to be created for an already-evicted
  // principal, which manufactured session residue even on platforms whose eviction
  // cascades sessions (ALXBA was spuriously SAT).
  s not in Open and s.s_from in Live and s.s_sub in Member
  Open' = Open + s
  Member'=Member and Evicted'=Evicted and Live'=Live and Armed'=Armed and Trigger'=Trigger
}
pred arm[a: Auto] {
  a not in Armed and a.a_author in Member
  some g: Live | g.g_sub = a.a_author and g.g_dev = a.a_dev
  Armed' = Armed + a and Trigger' = Trigger + a.a_author
  Member'=Member and Evicted'=Evicted and Live'=Live and Open'=Open
}
// THE transition. Membership always ends; everything else is platform-dependent.
pred evict[p: Principal] {
  p in Member and p != Owner
  Member' = Member - p
  Evicted' = Evicted + p
  (CascGrants   in Cascades) implies Live'    = Live    - { g: Grant | g.g_sub = p }    else Live'    = Live
  (CascSessions in Cascades) implies Open'    = Open    - { s: Session | s.s_sub = p }  else Open'    = Open
  (CascAutos    in Cascades) implies Armed'   = Armed   - { a: Auto | a.a_author = p }  else Armed'   = Armed
  (CascTriggers in Cascades) implies Trigger' = Trigger - p                             else Trigger' = Trigger
}
// BASELINE B1: the documented remediation, applied by hand.
pred revokeGrant[g: Grant] {
  g in Live
  Live' = Live - g
  Member'=Member and Evicted'=Evicted and Open'=Open and Armed'=Armed and Trigger'=Trigger
}
pred stutter {
  Member'=Member and Evicted'=Evicted and Live'=Live and Open'=Open and Armed'=Armed and Trigger'=Trigger
}
fact init { Member = Owner and no Evicted and no Live and no Open and no Armed and no Trigger }
fact transitions {
  always ( stutter
    or (some p: Principal | admit[p] or evict[p])
    or (some g: Grant | grant[g] or revokeGrant[g])
    or (some s: Session | openSession[s])
    or (some a: Auto | arm[a]) )
}

/* ---- platform semantics, sourced from the M1 harvest ---------------------- */
// Google Home: DETERMINED. Removal ends membership and app-mediated access.
// Documented NOT to cascade: lock passcodes (R1) and the Google TV binding (R2).
// GH session cascade is CONTINGENT (E2.6): removal is documented, but whether the
// removed member's app SESSION terminates is not addressed. Reading B is evidentially
// favoured -- R2 documents that at least one session type (Google TV) DOES persist.
pred P_GoogleHome_A { Cascades = CascGrants + CascSessions }   // sessions terminate
pred P_GoogleHome_B { Cascades = CascGrants }                  // sessions persist
// Alexa: SILENT on whether removal cascades to smart-home device control.
// Alexa has TWO silent dimensions on the same transition (grant cascade AND session
// cascade), so the reading set is the 2x2. Bounded, and enumerated per-transition
// rather than globally, per design C6.
pred P_Alexa_AA { Cascades = CascGrants + CascSessions }
pred P_Alexa_AB { Cascades = CascGrants }
pred P_Alexa_BA { Cascades = CascSessions }
pred P_Alexa_BB { Cascades = none }
// SmartThings: DETERMINED that device control ends; SILENT on member-authored Routines.
pred P_SmartThings_A { Cascades = CascGrants + CascAutos }     // reading A: Routines die
pred P_SmartThings_B { Cascades = CascGrants }                 // reading B: Routines survive
// Home Assistant: DETERMINED at L2 and CONFIRMED at L3. Tokens invalid for NEW auth,
// but the already-open socket survives read-only.
pred P_HomeAssistant { Cascades = CascGrants + SessReadOnly }

/* ---- residue probes, PATH-DISCRIMINATING ---------------------------------
   The design's metric instrument (section 1.7) requires that a result localise
   WHICH channel carried the authority. An undifferentiated "residue exists" is
   not an instrument -- it returned SAT for every platform and told us nothing.
   These probes name the channel and the capability level. */

pred evictedUnderB1[p: Principal] { p in Evicted and (no g: Live | g.g_sub = p) }

// Residue carried by the SESSION channel and by nothing else.
pred resSession[c: Cap] { some p: Principal, d: Device |
  eventually (evictedUnderB1[p] and effectViaSession[p,d,c]
              and not effectViaGrant[p,d,c] and not effectViaAutomation[p,d,c]) }
// Residue carried by the DEPUTY-AUTOMATION channel and by nothing else.
pred resAuto[c: Cap] { some p: Principal, d: Device |
  eventually (evictedUnderB1[p] and effectViaAutomation[p,d,c]
              and not effectViaGrant[p,d,c] and not effectViaSession[p,d,c]) }
// Deputy residue where the automation's author is SOMEONE ELSE: the removed
// principal's surviving trigger entity fires another member's rule. Strongest
// form of Def.4 clause (v) -- no surviving object names p in the authorization path.
pred resAutoForeign[c: Cap] { some p: Principal, d: Device |
  eventually (evictedUnderB1[p] and p in Trigger
              and (some a: Armed | a.a_dev = d and c in a.a_cap.dominates and a.a_author != p)
              and not effectViaGrant[p,d,c] and not effectViaSession[p,d,c]) }

run GHA_sess_act  { P_GoogleHome_A and resSession[Operate] } for 4 but 3 Principal, 2 Device, 3 Grant, 2 Session, 2 Auto, 10 steps
run GHB_sess_act  { P_GoogleHome_B and resSession[Operate] } for 4 but 3 Principal, 2 Device, 3 Grant, 2 Session, 2 Auto, 10 steps
run GHA_auto_act  { P_GoogleHome_A and resAuto[Operate]    } for 4 but 3 Principal, 2 Device, 3 Grant, 2 Session, 2 Auto, 10 steps
run GHB_auto_act  { P_GoogleHome_B and resAuto[Operate]    } for 4 but 3 Principal, 2 Device, 3 Grant, 2 Session, 2 Auto, 10 steps
run ALXAA_sess_act { P_Alexa_AA and resSession[Operate] } for 4 but 3 Principal, 2 Device, 3 Grant, 2 Session, 2 Auto, 10 steps
run ALXAB_sess_act { P_Alexa_AB and resSession[Operate] } for 4 but 3 Principal, 2 Device, 3 Grant, 2 Session, 2 Auto, 10 steps
run ALXBA_sess_act { P_Alexa_BA and resSession[Operate] } for 4 but 3 Principal, 2 Device, 3 Grant, 2 Session, 2 Auto, 10 steps
run ALXBB_sess_act { P_Alexa_BB and resSession[Operate] } for 4 but 3 Principal, 2 Device, 3 Grant, 2 Session, 2 Auto, 10 steps
run STA_auto_act    { P_SmartThings_A and resAuto[Operate]    } for 4 but 3 Principal, 2 Device, 3 Grant, 2 Session, 2 Auto, 10 steps
run STA_foreign_act { P_SmartThings_A and resAutoForeign[Operate] } for 4 but 3 Principal, 2 Device, 3 Grant, 2 Session, 2 Auto, 10 steps
run STB_auto_act    { P_SmartThings_B and resAuto[Operate]    } for 4 but 3 Principal, 2 Device, 3 Grant, 2 Session, 2 Auto, 10 steps
run HA_sess_read    { P_HomeAssistant and resSession[View]    } for 4 but 3 Principal, 2 Device, 3 Grant, 2 Session, 2 Auto, 10 steps
run HA_sess_act     { P_HomeAssistant and resSession[Operate] } for 4 but 3 Principal, 2 Device, 3 Grant, 2 Session, 2 Auto, 10 steps
run HA_auto_act     { P_HomeAssistant and resAuto[Operate]    } for 4 but 3 Principal, 2 Device, 3 Grant, 2 Session, 2 Auto, 10 steps

/* E4.4 — SCOPE ESCALATION. Design insight I5 claims the small-scope hypothesis is
   well-founded here because households are small. That is a claim, so test it: if the
   HA deputy residue is genuinely small-scope, it must still be found at larger scopes
   and no NEW qualitative behaviour should appear. */
run HA_auto_scope6  { P_HomeAssistant and resAuto[Operate] } for 6 but 6 Principal, 4 Device, 6 Grant, 4 Session, 4 Auto, 12 steps
run HA_auto_scope8  { P_HomeAssistant and resAuto[Operate] } for 8 but 8 Principal, 5 Device, 8 Grant, 5 Session, 5 Auto, 14 steps
run HA_sessact_scope8 { P_HomeAssistant and resSession[Operate] } for 8 but 8 Principal, 5 Device, 8 Grant, 5 Session, 5 Auto, 14 steps
