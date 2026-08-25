/*
  E2.8 / E2.9 / E6.6 — the two residue channels the platform model did not yet carry,
  plus the cascade-remediation ablation.

  E2.8 STANDING CREDENTIAL (Google Home R1). A smart-lock passcode is not a grant and
  not a session: it is a credential held by the DEVICE, issued to a person, and
  evaluated by the lock without reference to household membership. Google documents
  that removal does NOT invalidate it.

  E2.9 SECONDARY-ECOSYSTEM BINDING (R2 / design SC-5). A device admitted to two
  ecosystems has two independent grant stores. Removal from one cannot cascade to the
  other -- structurally, not by oversight. FABRICPROOF's multi-admin Matter result is
  IMPORTED as the assumption that a device legitimately holds two admins; it is not
  re-derived here (decision D3).
*/
module tenantsafe_channels

abstract sig Cap {}
one sig View, Operate, Manage, Administer extends Cap {}
fun dominates : Cap -> Cap {
    View->View + Operate->Operate + Manage->Manage + Administer->Administer
  + Operate->View + Manage->View + Manage->Operate
  + Administer->View + Administer->Operate + Administer->Manage }

sig Principal {}
sig Device {}
sig Passcode { pc_holder: Principal, pc_dev: Device }          // E2.8 standing credential
sig Binding  { b_dev: Device, b_admin: Principal }             // E2.9 secondary ecosystem

var sig Member  in Principal {}
var sig Evicted in Principal {}
var sig LiveCode in Passcode {}
var sig LiveBind in Binding  {}
one sig Owner in Principal {}

abstract sig Flag {}
one sig CascPasscodes, CascBindings extends Flag {}
sig Cascades in Flag {}
fact wf { Owner not in Evicted  always (Cascades' = Cascades) }

// A passcode opens the lock regardless of membership; a binding actuates via the
// other ecosystem regardless of this one's member list.
pred effectViaPasscode[p: Principal, d: Device] { some c: LiveCode | c.pc_holder=p and c.pc_dev=d }
pred effectViaBinding [p: Principal, d: Device] { some b: LiveBind | b.b_admin =p and b.b_dev =d }

pred admit[p: Principal] { p not in Member and p not in Evicted
  Member'=Member+p and Evicted'=Evicted and LiveCode'=LiveCode and LiveBind'=LiveBind }
pred issueCode[c: Passcode] { c not in LiveCode and c.pc_holder in Member
  LiveCode'=LiveCode+c and Member'=Member and Evicted'=Evicted and LiveBind'=LiveBind }
pred addBinding[b: Binding] { b not in LiveBind and b.b_admin in Member
  LiveBind'=LiveBind+b and Member'=Member and Evicted'=Evicted and LiveCode'=LiveCode }
pred evict[p: Principal] { p in Member and p != Owner
  Member'=Member-p and Evicted'=Evicted+p
  (CascPasscodes in Cascades) implies LiveCode' = LiveCode - { c: Passcode | c.pc_holder=p } else LiveCode'=LiveCode
  (CascBindings  in Cascades) implies LiveBind' = LiveBind - { b: Binding  | b.b_admin =p } else LiveBind'=LiveBind }
pred stutter { Member'=Member and Evicted'=Evicted and LiveCode'=LiveCode and LiveBind'=LiveBind }
fact init { Member=Owner and no Evicted and no LiveCode and no LiveBind }
fact trans { always ( stutter or (some p: Principal | admit[p] or evict[p])
  or (some c: Passcode | issueCode[c]) or (some b: Binding | addBinding[b]) ) }

pred passcodeResidue { some p: Principal, d: Device | eventually (p in Evicted and effectViaPasscode[p,d]) }
pred bindingResidue  { some p: Principal, d: Device | eventually (p in Evicted and effectViaBinding [p,d]) }

// Documented Google Home semantics: neither cascades.
pred P_GH_documented { Cascades = none }
// E6.6 ablation A-4: add cascade-on-removal and measure what it eliminates.
pred A4_cascade_passcodes { Cascades = CascPasscodes }
pred A4_cascade_bindings  { Cascades = CascBindings }
pred A4_cascade_both      { Cascades = CascPasscodes + CascBindings }

run E28_passcode_documented { P_GH_documented and passcodeResidue } for 4 but 3 Principal, 2 Device, 3 Passcode, 3 Binding, 8 steps
run E29_binding_documented  { P_GH_documented and bindingResidue  } for 4 but 3 Principal, 2 Device, 3 Passcode, 3 Binding, 8 steps
run E66_passcode_cascaded   { A4_cascade_passcodes and passcodeResidue } for 4 but 3 Principal, 2 Device, 3 Passcode, 3 Binding, 8 steps
run E66_binding_cascaded    { A4_cascade_bindings  and bindingResidue  } for 4 but 3 Principal, 2 Device, 3 Passcode, 3 Binding, 8 steps
run E66_both_cascaded_pc    { A4_cascade_both and passcodeResidue } for 4 but 3 Principal, 2 Device, 3 Passcode, 3 Binding, 8 steps
run E66_both_cascaded_bind  { A4_cascade_both and bindingResidue  } for 4 but 3 Principal, 2 Device, 3 Passcode, 3 Binding, 8 steps
