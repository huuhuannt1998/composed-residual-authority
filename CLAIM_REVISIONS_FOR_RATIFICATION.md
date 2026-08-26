# Claim revisions awaiting PI ratification

Raised as `chk_01M0ZCJJMNXZS4MVKGAZY4CY3N`. Nothing below is bound. Ratified
wording is not rewritten by a changed dependency; these are drafts for you to
accept, amend, or reject.

**Context worth having first: C4 was already correct.** It states that
re-resolution reduces the residue to two and session termination to zero. The
prose in §1, §8, §9 and §11 had drifted away from it and credited re-resolution
with closing everything. The paper contradicted its own ratified claim, and the
prose was corrected to match the claim rather than the reverse. The spine held.

---

## C2 → v3 (currently v2, ratified by `dec_01M0SEBCRD5Z4N37YX5TQJYJF1`)

**Why:** bound to Home Assistant **2026.7.4** and to a single-trace
confirmation. The evidence is now 2026.8.3 with thirty independent trials per
arm and a six-hour persistence measurement. The substance is unchanged and
strengthened; the version string and the strength of evidence are stale.

> On Home Assistant 2026.8.3, deleting a user does not terminate that user's
> already-open authenticated session, which retains read access to all entity
> state and to the live event stream. Across thirty independent trials per arm
> every measured cell is deterministic: a deleted administrator retains six of
> eight operations, direct actuation is refused in all thirty trials, and
> actuation induced by firing an event that triggers a household automation
> succeeds in all thirty. For that induced actuation the minimal sufficient
> support has size two, because neither the session nor the automation alone
> puts the effect within reach. The residue is unchanged at every delay point
> measured out to six hours and survives both automation and integration
> reload; only a full platform restart ends it.

*Add to prohibited wording:* `the residue never expires` ·
`the residue is permanent` · `no action can end the residue`

---

## C4 → v4 (currently v3, ratified by `dec_01M0SF58HPSCRH90Y1Y42PGY14`)

**Why:** says "ten legitimate operations"; the suite is now twenty-two tests
across seven groups. C4 also predates the corrected performance measurement,
whose result is a **null**.

> Across the observable post-removal capability surface on Home Assistant
> 2026.8.3, the unmodified platform leaves eight capabilities reachable by a
> deleted principal; re-resolving the principal at each authorization decision
> reduces this to two, both on the event-forwarding path, and terminating the
> session on removal reduces it to zero. A twenty-two test lifecycle regression
> suite passes in full under session termination with no security and no
> functional regressions, and returns twenty-two of twenty-two against two
> security regressions on the unpatched baseline. Neither defense shows a
> latency difference from baseline that five runs of ten thousand operations per
> arm can resolve.

*Add to prohibited wording* — the existing guard
`re-resolution closes all residual capabilities` was correct but string-matching
missed the paraphrase that reached the draft:
`closes both observed residues` · `so small a change closes the residue` ·
`the monitor closes the residue` · `the defenses are faster` ·
`terminating the session improves latency`

---

## C5 — new

**Why:** the cross-platform result is asserted in the abstract, the introduction
and §7 on the strength of `dec_01M0X71HWPRH37BWBPMFE2NK7K`, but no claim covers
it. **This is the change that most alters what the paper claims** — it moves the
contribution from a single-platform case study to a two-ecosystem finding, so it
should be ratified explicitly rather than inherited from a decision record.

> Validating a credential when a connection is established and not re-checking
> it afterwards is not specific to one implementation. On openHAB 4.3.2, built
> independently of Home Assistant, removing an account correctly refuses that
> account's API token on every request path, while a server-sent event stream
> opened before the removal continues to deliver in five independent trials of
> five; the platform's own session-clearing command does not close it either.
> Home Assistant is likewise clean on its request paths, so in both systems the
> defect is confined to connections established before the transition.

*Prohibited wording:*
`all smart-home platforms share this defect` ·
`we surveyed the smart-home ecosystem` ·
`the phenomenon is universal` ·
`openHAB and Home Assistant are equally affected` ·
`Google Home, Alexa and SmartThings were confirmed at runtime` ·
`every platform validates credentials only at connection setup`

**Scope language that must survive any edit:** Google Home, Alexa and
SmartThings contribute documented-semantics evidence only and were not observed.
Two runtime ecosystems is not a survey.
