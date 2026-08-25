# TENANTSAFE — Experiment Checklist

`prj_01M0EEDR6PYRHSPSG2VF68D7EM` · updated 2026-08-21 · staging per `research_design_detailed.md` §11.1

**Legend** `[x]` done · `[~]` partial / defective · `[ ]` not started · `[!]` blocked on a decision · `[×]` cancelled

**Hardware:** none, ever. Everything below runs on the M4 (Tamarin 1.12, Alloy 6.2, TLC 1.8, Docker).

---

## Phase M1 — Scoping gate  ✅ COMPLETE

- [x] **E1.1** Scoop audit vs multi-user access control (instant vs transition axis) — GO. `jrn_01M0EEEDBA2BKR941H551308X0`
- [x] **E1.2** Scoop audit vs smart-home formal methods (identification vs authority) + disambiguation paragraph — GO
- [x] **E1.3** KRATOS / Zeng-Roesner lineage check for transition work — none found
- [x] **E1.4** IPV-and-technology check for formalized revocation — none found
- [x] **E1.5** Semantics harvest, 4 platforms × 6 transitions — 15 DETERMINED / 3 CONTINGENT / 6 SILENT. `jrn_01M0EGJ4FXWXYS49KSTG96NMGB` (superseded on R3 by `jrn_01M0HJTVJJM5W7JR52KGVGN3DW`)
- [x] **E1.6** Feasibility judgement on the documentation-only re-scope — GO, 4 platforms instantiable

---

## Stage 0 — Substrate  🟡 PARTIAL

- [x] **E0.1** Port FABRICPROOF substrate discipline (persistent vs linear facts) — `models/tenantsafe_base.spthy`
- [x] **E0.2** Alloy base model — `models/tenantsafe.als`
- [x] **E0.3** Alloy executability, 4 legitimate workflows — **4/4 SAT, <1s**
- [x] **E0.4** Tamarin base-model tractability test — **INTRACTABLE** (>4 min, no verdict, twice). Diagnostic, not a failure: it empirically justifies the design's tool split
- [x] **E0.5** Tamarin DNA theory executability — `exec_two_step_chain` VERIFIED (non-vacuous)
- [x] **E0.6** GTB timed model built — **in Alloy, not TLC**. Deviation from §5.0 recorded with reasons (a separate TLA+ spec would model a different system and re-open the C7 problem). `models/tenantsafe_time_transfer.als`
- [x] **E0.7** Conformance on the **shared fragment** (amended C7) — **20/20 PASS** (`coding/conformance.py`). Scope limit stated: covers the lattice + delegation narrowing only; residue channels and chain induction are not cross-checked

> ✅ **Stage 0 exit MET** (under the amended C7): executability passes on both arms, shared-fragment conformance 20/20.

---

## Stage 1 — Harvest + determinacy coding  🔴 MAJOR GAP

- [x] **E1.7** Documentation corpus assembled, 4 platforms
- [x] **E1.8** **7/10 sources snapshotted with SHA-256** (`coding/snapshots/MANIFEST.tsv`). 3 blocked by bot protection (SmartThings support, home-assistant.io ×2) — all have named substitutes (samsung.com mirror; HA source at L2)
- [~] **E1.9** Explicit codebook written (`coding/codebook.md`); blind re-code executed. **Still single-analyst** — see E1.13
- [x] **E1.10** **κ = 0.923**, CI [0.775, 1.000], 23/24 agreement — PASSES the ≥0.70 gate. ⚠️ intra-rater (test-retest), *not* inter-rater
- [x] **E1.11** Adjudication: 1 disagreement (SmartThings/`evict` D→**C**), resolved to C per codebook. **Tally corrected 15/3/6 → 14/3/7** (the original was arithmetically wrong)
- [ ] **E1.13** *(new)* True **inter-rater** reliability with a second independent analyst
- [x] **E1.12** Amazon pages now fetch **HTTP 200** with a browser UA and are hashed. SmartThings support still 403 — samsung.com mirror used and recorded

> 🟡 **Partly closed.** A codebook now exists, the coding is reproducible, κ passes, and a real error was caught (both a wrong tally and a miscoded cell). But κ here is **test-retest by one analyst**, which is systematically optimistic. C-C still needs E1.13 before the paper can claim inter-rater reliability.

---

## Stage 2 — Per-platform instantiation  🟡 PARTIAL

- [x] **E2.1** Cascade-set encoding of platform semantics — `models/tenantsafe_platforms.als`
- [x] **E2.2** Path-discriminating residue probes (channel × capability)
- [x] **E2.3** Home Assistant instantiation from L3 evidence — **`HA_sess_act` UNSAT, `HA_sess_read` SAT**; model reproduces measured behaviour
- [x] **E2.4** SmartThings dual readings (A: Routines cascade / B: survive) — both SAT on deputy channel
- [x] **E2.5** Alexa dual readings on membership cascade — both run
- [x] **E2.6** **DEFECT CLOSED.** Harvest shows both are CONTINGENT (GH documents Google TV sessions persisting but never the app session; Alexa doesn't address sessions). Both now dual-modelled: GH A=UNSAT/B=SAT, Alexa AA,BA=UNSAT / AB,BB=SAT — **truth flips ⇒ CONTINGENT**
- [~] **E2.7** Session-minting guard added (`s_sub in Member`) — fixed a spurious SAT. `disarm`/`unbindTrigger` still absent from the platform model
- [x] **E2.8** Standing-credential channel modelled (`tenantsafe_channels.als`) — passcode residue **SAT** under documented GH semantics
- [x] **E2.9** Secondary-ecosystem binding modelled — residue **SAT**. FABRICPROOF's multi-admin result imported as an assumption, not re-derived (D3)
- [x] **E2.10** Transfer instantiated, **both NRT directions**. A (prior owner): UNSAT with wipe / SAT without. B (new owner reads history): UNSAT with wipe / SAT without. **Both CONTINGENT**

---

## Stage 3 — 🚩 THE GATE  ⛔ NOT STARTED

*Gate RESOLVED 2026-08-22 → **EXIT-A**. Stage 6 unblocked and executed.*

- [~] **E3.1** 20-row verdict grid compiled (`coding/gate.py`). RC covered on `evict` across all 4 platforms; NRT/GTB/DNA probed platform-neutrally. **Not the full 4×6×4×2 sweep**
- [x] **E3.2** Residue presence + channel recorded per cell (path-discriminating probes)
- [x] **E3.3** CRD per residue: HA deputy = 2 (empirical), SmartThings deputy = 2, R1/R2/session channels = 1
- [x] **E3.4** `A5` necessity **PASS** on the HA deputy residue. Full witness → residue; minus socket → collapses; minus automation → collapses. **CRD=2 empirically**
- [x] **E3.5** Matched-budget single-object control satisfied by the two E3.4 arms — neither element alone reaches the effect at identical β
- [x] **E3.6** Severity assigned per cell against the frozen catalog (S0–S4); persistence P2 for the HA and GH cells
- [x] **E3.7** 🚩 **GATE FIRED: EXIT-A.** HA/`evict`/RC — S3, CRD=2, DETERMINED at L3, shipping release, A5 PASS. CONT=5 (below EXIT-B's 8)
- [!] Blocked on: E0.7 (conformance), E1.9–E1.10 (κ), E2.6–E2.7 (defects), and `chk_01M0HJVVM365YSPTQTT5S0HQJE` (severity catalog)

**Current standing (not a verdict):** ⚠️ **one cell now satisfies every EXIT-A conjunct** — Home Assistant deputy residue: S3 actuation, CRD=2 necessity-tested, DETERMINED at L3, shipping release. The gate is still a *sweep* verdict, not a single cell, and E1.9/E1.10, E0.7 and E2.6 remain open. The pre-registered EXIT-B lean is now under real pressure.

---

## Stage 4 — Unbounded proofs  🟡 PARTIAL

- [x] **E4.1** DNA, capability dimension — **VERIFIED**, 543 steps, inductive (`models/tenantsafe_dna.spthy`)
- [x] **E4.2** DNA, device dimension — **FALSIFIED**, 8-step trace. ⚠️ *by construction*; a model-capability result, **not** a platform verdict
- [x] **E4.3** **No platform exposes user-to-user re-delegation** (GH admin-only, ST owner-only, HA none, Alexa undocumented) ⇒ **DNA holds vacuously on all four**. Correct prior, uninteresting reason
- [x] **E4.4** Scope escalation to 6 and 8: HA deputy residue **still SAT**, `HA_sess_act` **still UNSAT**. No new qualitative behaviour ⇒ supports insight I5
- [x] **E4.5** **GTB CONTINGENT** — UNSAT when expiry cascades to the minted session, SAT when it doesn't. Three successive mis-statements of the property were caught by controls that should have been UNSAT and weren't
- [x] **E4.6** TTE realised as `expired[s.s_from]` — a session outliving its minting grant *is* TTE > 0

---

## Stage 5 — Scale  ⛔ NOT STARTED

- [x] **E5.1** Stratified generator, cascade semantics matched to the Alloy model (`coding/scale.py`)
- [x] **E5.2** N=9,000 (9 platform-readings × 1000), seed 20260822, Wilson CIs per platform
- [~] **E5.3** Mixed model fitted, random intercept on stratum, converged. ⚠️ **linear probability model, not logistic** — statsmodels `mixedlm` is linear; deviation from design §11.4
- [x] **E5.4** 70/30 split, held-out accuracy 0.660
- [~] **E5.5** Contrast 2 (composed share) = 0.449, CI [0.432, 0.465]. Contrasts 1/3/4/5 not run in the sampled arm

---

## Stage 6 — Reference monitor (M3)  ⛔ NOT STARTED

- [x] **E6.1** **TSMON implemented and applied** (`models/tsmon_patch.py`) — re-resolves the principal against the store at the two paths that skip it
- [x] **E6.2** Provenance realised as store re-resolution — the minimal correct fix, making `require_admin` and `_async_get_allowed_states` agree with `service.py:729`
- [x] **E6.3** **Both residues CLOSED** with a valid control: deputy `fire_event`→`unauthorized`, entity stays off; `get_states` n=19→0
- [~] **E6.4** TSMON decision cost **18.9 ns** (dict lookup), ~5 orders below the 1.2 ms WebSocket RTT. ⚠️ end-to-end arms were **unpaired across restarts** and uninterpretable; only the microbenchmark is sound
- [x] **E6.7** *(new, C5)* **Monitor false-positive test** — 10 legitimate operations across the household lifecycle, paired with/without TSMON. **10/10 succeed in both arms**; the monitor denies nothing a current principal may do (`experiments/e66_false_positive.py`)
- [x] **E6.5** **Ablation confirms the counterfactual** — TSMON reverted ⇒ both residues return (`fire_event` succeeds, entity=on, n=19)
- [x] **E6.6** Cascade-on-removal eliminates **100%** of both documented Google Home channels (passcode, binding) — the quantified vendor recommendation
- [!] Blocked on Stage 3 (what the monitor must enforce depends on the exit)

---

## Stage 7 — L3 confirmation arm (HA only)  🟡 PARTIAL

- [x] **E7.1** HA 2026.7.4 in Docker, isolated on :8124 — running
- [x] **E7.2** Source paths verified in the *shipping release*, not just `dev`
- [x] **E7.3** **R3 actuation probe — REFUTED.** `call_service` blocked, `UnknownUser`
- [x] **E7.4** **R3 read probe — CONFIRMED.** `get_states` 18/18, live events delivered, new subscriptions accepted
- [x] **E7.5** Deactivate control arm — connection closed in every case
- [x] **E7.6** **DEPUTY PATH CONFIRMED AT ACTUATION.** Orphaned socket `fire_event` → household automation → service call under the *automation's* context. `ts_probe=on`. First invalid run (non-admin control failed) discarded and redone with valid controls
- [x] **E7.6b** Admin-surface blast radius: `execute_script` **blocked** (performs a service call), `subscribe_trigger` and `config/auth/list` **survive** — a removed admin can still enumerate the household's users. `decorators.py:62` trusts the stale object; 389 `require_admin` usages tree-wide
- [x] **E7.7** Orphaned socket does **not** survive an HA restart (observed across every restart in Stage 6). Persistence is bounded by connection lifetime
- [x] **E7.8** Long-lived token: ACCEPTED pre-removal (control), `auth_invalid` after. Tokens genuinely invalidated for new auth
- [~] **E7.9** Divergence captured for `evict` (the consequential one): documentation describes neither the orphaned-socket read residue nor the deputy path. Other 5 transitions not systematically compared

---

## Mock-review response (SP2027 comprehensive review)  🟡 P0 DONE

> Compliance audited item-by-item against the review's own submission-blocking
> checklist on 2026-08-25 — see **`FEEDBACK_COMPLIANCE.md`**. The audit found two
> blocking omissions (model mutation testing, multiple-socket/token-revocation
> session conditions); both were closed the same day.

### P0 — fatal / critical
- [x] **R-P0.1** **Composition depth definition REPAIRED** — was a minimal *removal cut* (which gave CRD=1 and falsified CRA under our own definition); now minimal *sufficient support*. Machine-checked in `models/tenantsafe_crd.als`
- [x] **R-P0.2** Reachability made explicit — residue quantifies over `Reach_b(H')`
- [x] **R-P0.3** Induced-effect relation added — the removed principal never makes the call; the automation does
- [x] **R-P0.4** Audit projection `π_audit` moved into the definition, not limitations
- [x] **R-P0.5** Alloy assertions re-run under repaired definitions — 5/5 required outcomes
- [x] **R-P0.2b** **MODEL MUTATION TESTING** *(added 2026-08-25 — this P0 item was missing from the list entirely)* — `models/tenantsafe_mutants.als`, 8 mutants / 15 commands, **15/15 match the review's predicted verdicts**. M5 (session+automation) is the **only** mutant reported as CRA; M1/M4/M7 have residue and are correctly reported at depth 1. The instrument discriminates rather than reproducing one trace
- [x] **R-P0.6** **Full defense-completeness matrix** — baseline **8** residual capabilities, re-resolution **2**, session termination **0** (`experiments/p0e3_capability_matrix.py`)
- [!] **R-P0.7** Vulnerability disclosure — **PI declined** (research purposes); review lists it as policy-critical
- [x] **R-P0.8** **Related-work / novelty validation** — references **14 → 44** (venue norm 40–60). §2 reorganized into 15 labelled areas covering all twelve the review required, each analysed on its six dimensions, closing with a comparison table whose **composition column is empty for every prior line**. One real venue error found and fixed (`havron2019clinical` is USENIX Sec 2019, not IEEE S&P). Eight DOI-less USENIX/SOUPS entries cannot be approved by RKA's DOI-anchored validator — all independently confirmed in DBLP; documented as tooling drift #5, not bypassed

### P1
- [x] **R-P1.6** **Multi-version study** — signature *identical* across 2024.12 / 2026.6.4 / 2026.7.4 / 2026.8.3 (~20 months, incl. newest stable). Structural, not a regression
- [x] **R-P1.9** **Deputy generality** — 6/6 automation families actuate post-removal, **all authored by the owner** (review case A7): no surviving authorization object names the removed principal
- [x] **R-P1.10** **Defense comparison** — A (session termination) vs B (re-resolution), full matrix above
- [x] **R-P1.12** Functional regression — 10 legitimate operations pass under every condition
- [x] **R-P1.11** **Corrected end-to-end benchmark** — three simultaneous instances with matched restart counts and rotated arm order removes the restart confound. 5 runs × 10,000 ops/arm. **All 12 defense-vs-baseline CIs overlap baseline; no performance difference claimed.** Microbenchmark corrected for timer overhead: **25.6 ns** amortized (the 83 ns first reported was 57 ns of timer)
- [x] **R-P1.12b** **Lifecycle regression suite** — 7 groups / 22 tests. Defense A **22/22, 0 security and 0 functional regressions**; baseline 20/22 with **2 security regressions** (the vulnerability, reproduced by the suite)
- [x] **R-P1.14** **Reproducible documentation corpus** — `coding/verify_corpus.py`, 10/10 sha256 match, 0 drift
- [x] **R-P2.16** **SECOND RUNTIME ECOSYSTEM: openHAB 4.3.2** — clean on the request path, **residual on established SSE connections 5/5**, and `clearSessions` does not close it either. The defect class is not Home Assistant-specific
- [x] **R-P2.17** **Automated residue finder** — `tools/residue_finder.py` consumes a platform transition spec and returns witness, minimal support, CRD and audit-visible objects. Reproduces CRD=2 for HA and **agrees with the Alloy verdicts 10/10**; the cross-validation found and fixed a real gap (self-triggering automations)
- [x] **R-P2.18** **CRD > 2 synthetic validation** — depths 1, 2, 3 and 4 constructed and machine-checked, 14/14, each with its "no smaller sufficient support" check UNSAT
- [x] **R-P2.19** **Severity classification** — highest surviving capability per transition: member/delete → **View**, admin/delete → **Administer**, both deactivate arms → none
- [~] **R-P1.8** Residual lifetime — long-delay run in progress (schedule reaches +6h)
- [x] **R-P1.7b** **Session conditions** *(2026-08-25)* — `experiments/p1e7b_sessions.py`. **Both** concurrent sockets survive deletion. A fresh socket with the old token is refused (`auth_invalid`), as is a long-lived token. **Explicit refresh-token revocation DOES tear the connection down**; deactivation is complete on both existing and new connections. The defect is isolated to *one* path: deletion alone fails to invoke teardown machinery HA already owns
- [x] **R-P1.7** **Session × role × transition × operation matrix COMPLETE** — 30 independent runs/arm × 4 arms. Every cell 0/30 or 30/30 (Wilson CI [0.000,0.114] / [0.886,1.000]) — structural, not intermittent. `admin/delete` leaves **6 of 8** operations residual **including automation-induced actuation**, while **direct** actuation and script execution are blocked 0/30 — an independent corroboration of CRD=2. `user/delete` leaves read only. **Both deactivate arms are clean, 0/30 everywhere**
- [x] **R-P1.15** **Scope/budget sensitivity** — 4 scope/budget points S1→S4; **17/17 verdicts identical** while runtime grows 4.9s → 75.0s. Stated as bounded ("no new qualitative pattern *within the tested model*"), not as an unbounded proof
- [ ] **R-P1.13** Independent documentation coding *(same as E1.13)*

### P2
*(all four P2 items are now complete — see the P1 block above.)*

---

## M4 — Disclosure, artifact, manuscript  ⛔ NOT STARTED

- [!] **E8.1** Coordinated disclosure to Home Assistant for R3 — *PI decision, not taken*
- [ ] **E8.2** Vendor disclosure for any Stage 3 falsification
- [x] **E8.3** `results/tenantsafe_artifact.tar.gz` (2.1 MB) — models, coding scripts, seeds, checklist, results, design
- [ ] **E8.4** IPV advocacy input for safe-exit templates (decision D4)
- [ ] **E8.5** Doc re-verification + diff report in the two weeks before submission (C1)

---

## Blocked on you

| # | Decision | Blocks |
|---|---|---|
| 1 | **Severity catalog** — is covert surveillance below actuation for IPV? `chk_01M0HJVVM365YSPTQTT5S0HQJE` | E3.7 |
| 2 | **C7 amendment** — conformance on shared fragment only | E0.7 → Stage 0 exit |
| 3 | **GH/Alexa session semantics** — harvest again, or dual-model and report contingency? | E2.6 |
| 4 | **HA disclosure** — contact the project about R3 now or after Stage 3? | E8.1 |

---

## Tally

| Stage | Done | Partial | Left |
|---|---|---|---|
| M1 scoping | 6 | 0 | 0 |
| Stage 0 substrate | 5 | 0 | 2 |
| Stage 1 coding | 1 | 1 | 4 |
| Stage 2 instantiation | 5 | 1 | 4 |
| Stage 3 **gate** | 0 | 0 | 7 |
| Stage 4 unbounded | 2 | 0 | 4 |
| Stage 5 scale | 0 | 0 | 5 |
| Stage 6 monitor | 0 | 0 | 6 |
| Stage 7 confirmation | 5 | 0 | 4 |
| M4 output | 0 | 0 | 5 |
| **Total** | **24** | **2** | **41** |
