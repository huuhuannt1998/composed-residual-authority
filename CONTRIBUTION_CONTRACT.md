# Contribution Contract — awaiting PI ratification

`man_01M0EEM76BD6Q8T23AY0ZWC5ZX` · IEEE S&P · revision 4 · 2026-08-23

Four contribution claims, each bound to verified `clm_` evidence with typed roles.
**Exact wording** is what the paper may assert. **Prohibited wording** is the overclaim
boundary — the linter and the reviewer both check against it.

---

## C1 — the calculus *(methodological)*

**Exact.** Household authority can be formalized as a calculus over transition events in
which revocation-completeness is the emptiness of an authority residue, a statement that
access-control models evaluated at an instant cannot express because they have no
transition and no post-state.

**Prohibited.** "the calculus is sound and complete" · "we prove smart-home platforms are
secure" · "a complete formalization of smart-home access control" · "our model captures all
residual-access mechanisms"

**Evidence.** 3 support, 1 qualifier (no platform exposes re-delegation, so DNA holds vacuously).

---

## C2 — composed residual authority *(empirical — the headline)*

**Exact.** On Home Assistant 2026.7.4, deleting a user does not terminate that user's
already-open authenticated session, which retains read access to all entity state and the
live event stream; a deleted administrator can additionally cause device actuation by firing
an event that triggers a household automation, and the residue requires two surviving objects
because removing either one collapses it.

**Prohibited.** "remote exploit" · "authentication bypass" · "attackers can take over the
smart home" · "all smart-home platforms are affected" · "we eliminate residual access" ·
"this vulnerability allows unauthenticated access"

**Evidence.** 4 support (all L3-confirmed), 2 qualifier (the mechanism).

---

## C3 — determinacy *(empirical)*

**Exact.** Across four smart-home platforms and six household transitions, publicly
documented semantics leave three cells contingent and seven silent, and Google Home documents
two cases in which authority survives member removal rather than concealing them.

**Prohibited.** "platforms are universally under-specified" · "under-specification is the
dominant finding" · "inter-rater reliability" · "most platform behaviour is undefined" ·
"we surveyed all major smart-home platforms"

**Evidence.** 6 support, 2 qualifier, **1 counterevidence** — contingency span is 5, below
the pre-registered threshold of 8, so the project's own expectation that under-specification
would dominate is *not* borne out. This is bound as counterevidence deliberately.

---

## C4 — the monitor *(empirical)*

**Exact.** Applying the auth-store re-resolution that Home Assistant's service-call path
already performs, at the two paths that skip it, closes both observed residues on a running
instance at a measured cost of 18.9 nanoseconds per authorization decision, and reverting the
change makes both residues return.

**Prohibited.** "eliminates residual access" · "secures the smart home" · "model-agnostic" ·
"a verified reference monitor" · "prevents intimate-partner abuse" · "complete mediation"

**Evidence.** 2 support.

---

## Counterevidence disposition (required by readiness)

The C3 counterevidence — `CONT = 5 < 8` — is disclosed **in the Results section body**, not
a footnote: the paper states that its own pre-registered threshold for the under-specification
claim was not met, and that EXIT-A is carried by C2 rather than by C3. Public location:
`sections/06_determinacy.tex`.

## Remaining readiness blocks

| Block | Resolved by |
|---|---|
| `NO_ACTIVE_CLAIMS` | PI ratifies C1–C4 → state becomes `active` |
| `ORPHAN_RESULT_UNIT` ×3 | resolves once claims are active |
| `CHECKPOINT_REQUIRED` ×2 | venue + outline checkpoints |
| `RESULT_COUNTEREVIDENCE_REQUIRES_DISPOSITION` | the disposition above, once ratified |
