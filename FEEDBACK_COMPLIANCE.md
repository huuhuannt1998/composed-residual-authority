# Mock-review compliance tracker

Audits the manuscript and experiment set against every item in
`manuscripts/feedback/SP2027_mock_review_comprehensive.md`, section 25
("Submission-Blocking Checklist") and section 20 ("Experiment Priority Summary").

**Legend** ✅ done and evidenced · 🟡 partial (what is missing is stated) ·
❌ not done · ⛔ blocked (PI decision or unavailable resource)

**Last audited** 2026-08-25. Two P0/blocking omissions were found by this audit and
closed the same day: model mutation testing, and the multiple-socket /
token-revocation session conditions. They are marked **[NEW]** below.

---

## 1. Formal model — 9/9 ✅ (complete)

| # | Item | Status | Evidence |
|---|---|---|---|
| 1 | Replace current CRD definition | ✅ | `models/tenantsafe_crd.als` — minimal *sufficient support*, not minimal removal cut |
| 2 | Define minimal sufficient support | ✅ | `sufficientFor[S,c]` + minimality quantifier |
| 3 | Define reachable post-transition traces | ✅ | residue quantifies over `Reach_b(H')` |
| 4 | Define induced/causal effect | ✅ | review Option C, authority-carrier chain: principal → session → event → automation → service call |
| 5 | Define audit-visible authorization projection | ✅ | `π_audit(H)` in the definition, not in limitations |
| 6 | Re-run every model result | ✅ | R1 SAT · R2a UNSAT · R2b UNSAT · **R3 UNSAT** · R4 SAT · R5 SAT |
| 7 | **Add mutation tests** | ✅ **[NEW]** | `models/tenantsafe_mutants.als` — 8 mutants, 15 commands, **15/15 match the review's predicted verdicts** |
| 8 | Add scope/budget sensitivity | ✅ **[NEW]** | `experiments/p1e15_scope_sweep.sh` — 4 scope/budget points, **17/17 verdicts identical**, runtime 4.9 s → 75.0 s |
| 9 | Confirm HA witness has CRD exactly 2 | ✅ | R1 SAT (pair sufficient) ∧ R3 UNSAT (no smaller support) ⇒ CRD = 2 |

### Mutation matrix (P0 Experiment 2) — the instrument discriminates

| Mutant | Residue? | CRD | Audit-clean? | **CRA?** | Review expected | Match |
|---|---|---|---|---|---|---|
| M1 forgotten grant row | yes | 1 | no (Grant names *p*) | **false** | Res≠∅, CRA=false, depth 1 | ✅ |
| M2 surviving session only | read only | — (actuate UNSAT) | yes | **false** | residual read, no composed actuation | ✅ |
| M3 expired guest grant + session | read only | — | yes | **false** | residue iff session survives; expired grant confers nothing (`M3_expired_alone` UNSAT) | ✅ |
| M4 secondary ecosystem binding | yes | 1 | yes | **false** | survives local membership removal | ✅ |
| M5 session + automation | yes | **2** | yes | **TRUE** | CRA=true, CRD=2 | ✅ |
| M6 correct cascading revocation | **none** | — | — | **false** | RC = true | ✅ |
| M7 broken cascade (only ACL removed) | yes | 1 | yes | **false** | RC = false | ✅ |
| M8 direct unauthorized service call | — | — | — | — | denied after removal (check UNSAT ⇒ holds) | ✅ |

M5 is the **only** mutant the instrument reports as composed residual authority.
M1, M4 and M7 all have residue and are all correctly reported at depth 1. This is
the anti-triviality property the review asked for: the model is not merely tailored
to reproduce the one Home Assistant trace.

### Scope/budget sensitivity (P1 Experiment 15)

| Scope | Bound | Runtime | Verdicts vs S1 |
|---|---|---:|---|
| S1 | 4 · 3P 2D 3G 2S 2A · 10 steps | 4.92 s | baseline |
| S2 | 5 · 4P 3D 4G 3S 3A · 12 steps | 9.34 s | **identical on all 17** |
| S3 | 6 · 5P 4D 5G 4S 4A · 14 steps | 21.38 s | **identical on all 17** |
| S4 | 7 · 6P 4D 6G 5S 5A · 16 steps | 75.00 s | **identical on all 17** |

Stated as the review requires — bounded, not a proof: *beyond scope S1, no new
qualitative residual-authority pattern appears within the tested model.* Runtime
grows ~15× while the verdict vector does not move, which is evidence the reported
per-platform signature is not an artifact of a tight bound.

---

## 2. Home Assistant — 13/13 ✅

| # | Item | Status | Evidence |
|---|---|---|---|
| 1 | Repeat critical experiments across independent runs | ✅ | `p1e7_matrix.py`, **30 runs/arm × 4 arms complete**; every cell 0/30 or 30/30 |
| 2 | Build full role/session/transition/operation matrix | ✅ | role×transition×operation (`p1e7_matrix.py`) + session conditions (`p1e7b_sessions.py`) |
| 3 | Test existing subscriptions after deletion | ✅ | measured on a distinct event type from new subscriptions |
| 4 | Test new subscriptions after deletion | ✅ | separate `mx_fresh` event so the two are never conflated |
| 5 | **Test multiple active sockets** | ✅ **[NEW]** | A1: **both** concurrent sockets survive deletion — residue is not per-socket |
| 6 | Test administrator and ordinary user | ✅ | both roles, both transitions |
| 7 | Run multi-version evaluation | ✅ | 2024.12 / 2026.6.4 / 2026.7.4 / 2026.8.3 — signature identical |
| 8 | Measure residual lifetime | ✅ **[NEW]** | out to **+6 h**, unchanged on all four channels; survives automation *and* integration reload; ends only on platform restart |
| 9 | **Test restart / network / token-revocation boundaries** | ✅ **[NEW]** | restart + drop (`p1e8`) and **explicit refresh-token revocation** (A4) |
| 10 | Test multiple automation/deputy forms | ✅ | 6/6 families actuate post-removal |
| 11 | Test household-authored automation | ✅ | all 6 owner-authored (review case A7) |
| 12 | Verify all residual channels close under patch | ✅ | Defense A: 8 → **0** residual capabilities |
| 13 | Revert patch and reproduce vulnerability | ✅ | `tsmon_unpatch.py`, baseline arm reproduces |

### Operation matrix (P1 Experiment 7) — Table B, 30 independent runs per arm

Residual = available **before** the transition **and** still available after. Cells the
role never had pre-transition are reported `n/a`, never counted as zero residue.

| Operation | user/delete | user/deactivate | admin/delete | admin/deactivate |
|---|---|---|---|---|
| read state | **30/30** | 0/30 | **30/30** | 0/30 |
| new subscription | 0/30 | 0/30 | **30/30** | 0/30 |
| pre-existing stream | **30/30** | 0/30 | **30/30** | 0/30 |
| list users | n/a | n/a | **30/30** | 0/30 |
| direct actuation | 0/30 | 0/30 | **0/30** | 0/30 |
| script execution | n/a | n/a | **0/30** | 0/30 |
| fire event | n/a | n/a | **30/30** | 0/30 |
| **automation-induced actuation** | n/a | n/a | **30/30** | 0/30 |

Wilson 95% CI is [0.886, 1.000] for every 30/30 and [0.000, 0.114] for every 0/30.
No cell is intermediate — the phenomenon is structural, not intermittent.

Three things this establishes:

1. **The residue is role-graded.** An ordinary member retains read only (depth 1).
   An administrator retains six of eight operations. Severity scales with the role
   held at the moment of removal.
2. **It corroborates CRD = 2 independently of the model.** Direct actuation and
   script execution are blocked 0/30 even for a deleted administrator, while
   automation-induced actuation succeeds 30/30. Actuation is reachable *only*
   through the composed path — which is exactly what R2a/R2b return UNSAT for.
3. **Both deactivate arms are completely clean**, 0/30 on every operation.

---

### Session-condition arms (P1 Exp 7b) — the defect is one path, not four

| Arm | Pre (socket/read/actuate) | Post | Reading |
|---|---|---|---|
| A1 two sockets, then delete — socket #1 | 1/1/1 | **1/1/1** | survives |
| A1 two sockets, then delete — socket #2 | 1/1/1 | **1/1/1** | survives — every live socket, not just one |
| A2 fresh socket, old token, after delete | 1/1/1 | 0/0/0 | `auth_invalid` — the **token** is invalidated |
| A3 long-lived token — original socket | 1/1/1 | **1/1/1** | survives |
| A3 long-lived token — fresh socket | — | 0/0/0 | `auth_invalid` — LLATs are revoked too |
| A4 **explicit refresh-token revocation** | 1/1/1 | 0/0/0 | connection **is** torn down |
| A5 deactivate — original socket | 1/1/1 | 0/0/0 | complete |
| A5 deactivate — fresh socket | — | 0/0/0 | `auth_invalid` — complete |

This isolates the defect precisely. Deactivation, explicit token revocation, and
new-connection authentication are all **complete**; only **user deletion** leaves
established connections alive. Home Assistant already owns the teardown machinery
(A4 exercises it) — deletion simply does not invoke it. That is both a sharper
claim than "revocation is incomplete" and direct support for Defense A.

---

## 3. Defense — 7/7 ✅

| # | Item | Status | Evidence |
|---|---|---|---|
| 1 | Implement session-termination defense | ✅ | Defense A, `models/tsmon_defenseA.py` |
| 2 | Implement / retest re-resolution defense | ✅ | Defense B, `models/tsmon_patch.py` |
| 3 | Compare security coverage | ✅ | baseline **8** → B **2** → A **0** residual capabilities |
| 4 | Compare code complexity | ✅ **[NEW]** | A: **1** call site, 2 functional lines. B: **2** call sites, 65-line patch. A dominates B on both security and complexity |
| 5 | Redo performance benchmark correctly | ✅ **[NEW]** | 3 simultaneous instances, matched restarts, rotated arm order — confound removed |
| 6 | Report p50/p95/p99 | ✅ **[NEW]** | all 4 operations × 3 arms; **all 12 CIs overlap baseline, no difference claimed** |
| 7 | Run full regression suite | ✅ **[NEW]** | 7-group / 22-test lifecycle suite. Defense A **22/22, 0 regressions**; baseline 20/22 with **2 security regressions** |

---

## 4. Documentation study — 7 ✅ / 1 🟡 / 1 ⛔

| # | Item | Status | Evidence |
|---|---|---|---|
| 1 | Freeze corpus | ✅ **[NEW]** | `coding/verify_corpus.py` re-verifies every sha256 — **10/10 match**, 0 drifted |
| 2 | Archive every source | ✅ **[NEW]** | all 10 sources in `sources.txt` have a snapshot; verifier reports 0 missing |
| 3 | Add exact collection dates | ✅ | `MANIFEST.tsv` |
| 4 | **Add independent second coder** | ⛔ | requires a second human analyst — the one item on this list I cannot perform |
| 5 | Compute inter-rater agreement | 🟡 | κ = 0.923, 95% CI [0.775, 1.000], 23/24 — but a **same-analyst blinded recode**, not independent. Reported as such |
| 6 | Adjudicate disagreements | ✅ | the one disagreement (SmartThings/`evict`, D→C) adjudicated and propagated |
| 7 | Release codebook | ✅ | `coding/codebook.md` |
| 8 | Resolve 24-cell vs 20-row inconsistency | ✅ | 4 platforms × 6 transitions = **24** cells; tally 14 D + 3 C + 7 S = 24 ✓ |
| 9 | Verify preregistration terminology | ✅ | prohibited-wording lint clean |

---

## 5. Related work — 9/9 ✅

References **14 → 44**, reaching the low end of the 40–60 venue norm the review
cited. Every added entry went through the same validation pipeline.

| Area required by the review | Status | Cited |
|---|---|---|
| Shared-IoT revocation / situational access | ✅ | `schuster2018situational`, `alrawi2019sok` |
| Remote binding & device lifecycle | ✅ | `fernandes2016security`, `zhou2019discovering` |
| Cross-cloud / trigger-action delegation | ✅ | `fernandes2018decentralized`, `bastys2018ifthis`, `wang2019charting` |
| Session invalidation | ✅ | `ghasemisharif2018single`, `sun2012devil`, `wang2012signing` |
| Continuous authorization / usage control | ✅ | `park2004ucon`, `zhang2005formal` |
| Confused deputy | ✅ | `hardy1988confused`, `felt2011permission` |
| Capability revocation | ✅ | `dennis1966programming`, `watson2015cheri` |
| Authorization provenance | ✅ | `bates2015trustworthy`, `wang2018fear` |
| Narrow classical-safety claims | ✅ | `harrison1976protection`, `sandhu1992typed`, `sandhu1996rbac`, `li2006security` |

Also added: multi-user smart home (`he2018rethinking`, `geeng2019whos`,
`zeng2017enduser`), mechanized IoT safety (`celik2018soteria`,
`celik2019iotguard`, `nguyen2018iotsan`), and technology-facilitated abuse
(`tseng2020tools`, `havron2019clinical`, `chatterjee2018spyware`).

§2 is now organized as 15 labelled areas, each analysed on the review's six
dimensions, closing with Table \ref{tab:related} — a comparison across four
dimensions (models transitions / post-transition reachability / composed
carriers / audit-visible vs effective authority). **Composition is empty for
every prior line**, which is the intersection argument the review asked for and
is more defensible than asserting novelty in prose.

### Two reference issues found and handled

**A real error, corrected.** `havron2019clinical` was recorded as IEEE S&P 2019.
It is USENIX Security 2019. Found by cross-checking every bibliography venue
against validated source metadata rather than against recall; corrected in the
bibliography, the venue map, and the RKA literature entry.

**A tooling limitation, documented not bypassed.** RKA's reference validation is
DOI-anchored, and USENIX/SOUPS mint no DOIs — so 8 entries sit at
`LOW_CONFIDENCE` with a single source, and `ghasemisharif2018single` is labelled
`HALLUCINATED`. That label is a **false positive**: the paper is indexed in DBLP
with exact title, all five authors, year, venue and canonical publisher URL.
All 8 were independently confirmed against DBLP. Attaching the canonical URL and
re-queueing does not move the verdict, because the pipeline does not treat `url`
as an identity anchor — this is fixable only in the pipeline. Recorded as
`jrn_01M0WBGF5A9NNRJ1RP4K2GWWT3`. `verify_citations.py` will BLOCK on these 8
until the pipeline accepts DBLP for DOI-less venues; that is a **PI decision**,
not something to route around.

## 6. Ethics / disclosure — 1 ✅ / 4 ⛔

| # | Item | Status | Note |
|---|---|---|---|
| 1–4 | Disclose to Home Assistant; record date; track response; update status | ⛔ | **PI declined** (2026-08-2x): "I do not want to send anything to anybody. This is for research purposes." Report is written and held at `disclosure/home-assistant-2026-08-23.md`, unsent. The review classes this policy-critical; it is a standing PI decision, recorded not overridden |
| 5 | Avoid unnecessary operational exploit detail | ✅ | ethics decision D4; defensive writing throughout |

---

## 7. Writing — 9/9 ✅

Center on composed residual authority ✅ · direct vs induced effect ✅ ·
ordinary/hidden/composed residue distinguished ✅ · audit-visible formulation
replaces "no object names *p*" ✅ · novelty narrowed ✅ · attack/provenance
figure ✅ · vacuous delegation result de-emphasised ✅ · documentation vs runtime
claims separated ✅ · **expand related work substantially ✅** (14 → 44 references).

---

## 8. Experiment priority summary (review §20)

| Pri | Experiment | Status |
|---|---|---|
| P0 | 1 · Repair + revalidate formal model | ✅ |
| P0 | 2 · **Model mutation testing** | ✅ **[NEW]** 15/15 |
| P0 | 3 · Full defense-completeness evaluation | ✅ 8 → 2 → 0 |
| P0 | 4 · Vulnerability disclosure | ⛔ PI declined |
| P0 | 5 · Related-work / novelty validation | ✅ 14 → 44 refs, 12 areas, comparison table |
| P1 | 6 · HA multi-version study | ✅ 4 versions |
| P1 | 7 · Session×role×transition×operation matrix | ✅ 30/arm, deterministic |
| P1 | 8 · Residual lifetime | ✅ **[NEW]** intact at +6 h; no time-based expiry |
| P1 | 9 · Automation/deputy generality | ✅ 6/6, all owner-authored |
| P1 | 10 · Compare two defenses | ✅ security + complexity |
| P1 | 11 · Correct end-to-end benchmark | ✅ **[NEW]** no difference beyond noise |
| P1 | 12 · Functional regression suite | ✅ **[NEW]** 22 tests, 0 regressions on Defense A |
| P1 | 13 · Independent documentation coding | ⛔ needs 2nd human |
| P1 | 14 · Reproducible documentation corpus | ✅ **[NEW]** 10/10 hashes verified |
| P1 | 15 · Scope/budget sensitivity | ✅ **[NEW]** 17/17 identical, S1→S4 |
| P2 | 16 · Second runtime ecosystem | ✅ **[NEW]** openHAB 4.3.2, residual 5/5 on persistent connections |
| P2 | 17 · Automated residue finder | ✅ **[NEW]** `tools/residue_finder.py`, agrees with Alloy 10/10 |
| P2 | 18 · CRD > 2 synthetic validation | ✅ **[NEW]** depths 1/2/3/4 machine-checked, 14/14 |
| P2 | 19 · Severity classification | ✅ **[NEW]** highest surviving capability per transition |

---

## 9. Required results tables (review §23) — 7/7 ✅

| Table | Required | Status |
|---|---|---|
| A | Platform semantics | ✅ **[NEW]** `tab:determinacy`, 4×6 grid with code definitions |
| B | HA full operation matrix | ✅ `tab:matrix`, 30 trials/arm |
| C | Version study | ✅ `tab:versions` |
| D | Residual lifetime | ✅ **[NEW]** `tab:lifetime`, full series to +6 h plus termination events |
| E | Composition ablation | ✅ `tab:support` |
| F | Defense comparison | ✅ `tab:defenses` — now carries p50 latency per operation |
| G | Alloy validation | ✅ `tab:alloyvalidation` — composition, depths 1–4, all 8 mutants |

## 10. Artifact package (review §24) — ✅

Built to the structure the review specifies: `artifact/` with `models/`
(incl. `mutants/` and `expected-results/`), `home-assistant/` (docker, versions,
scripts, probes, both patches), `experiments/` (version-study, operation-matrix,
lifetime, performance, regression, second-ecosystem), `docs-corpus/`, `coding/`,
`analysis/`, `tools/`, `results/`. 158 files, 2.2 MB bundle,
`results/tenantsafe_artifact.tar.gz`. The README reproduces the headline results
in five commands and states expected outputs for each.

Two things the README says plainly rather than glossing: the two coding passes
are the **same analyst** (files are named `pass1_original.csv` /
`pass2_blind_recode.csv`, never `coder1`/`coder2`), and the microbenchmark
reports both a timer-inclusive and a calibrated estimator so neither is
presented as the other.

## 11. Manuscript gate state

| Gate | Result |
|---|---|
| Pages | body **13/13**, total **15/18** — the CFP allows 13 body + 5 refs/appendices |
| Document class | `[conference,compsoc]` — **corrected**, was missing `compsoc` |
| Appendices | 4, using headroom the body limit does not charge for |
| Overfull boxes > 10pt | **0** (was 5, worst 129.6pt) |
| Undefined references / citations | **0** |
| Provenance | **0 blocks** |
| AI-tic | **12/12 PASS** |
| Prohibited wording | **PASS** |
| Layout | 0 blocks, 2 warns |
| References | 44, all validated |

## 12. What is left

**Every experiment on the review's checklist is now run.** What remains is not
mine to do:

- **Independent second coder.** Needs a second human analyst. Everything around
  it is ready — codebook released, both passes exported, reliability computed and
  correctly labelled intra-rater.
- **Vulnerability disclosure.** PI declined; the report is written and held
  unsent at `disclosure/home-assistant-2026-08-23.md`.
