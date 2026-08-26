# TENANTSAFE — Consolidated Results

Compiled 2026-08-22 · gate verdict **EXIT-A** · all results software-only, no hardware

---

## 1. Gate verdict

**EXIT-A**, carried by exactly one cell: **Home Assistant / `evict` / revocation-completeness**.
S3 (actuation) · CRD = 2 (necessity-tested empirically) · DETERMINED at L3 (verified
implementation) · shipping release 2026.7.4 · A5 necessity **and** matched-budget PASS.

`CONT = 5`, below the predeclared EXIT-B threshold of 8 — so had EXIT-A not fired, the
verdict would have been **EXIT-C, not EXIT-B**. The pre-registered expectation that
under-specification would dominate is *not* borne out at the threshold set for it.

---

## 2. The headline mechanism: authority laundering through a deputy

Home Assistant re-resolves `context.user_id` against the auth store on every **service
call** (`helpers/service.py:729`), so a removed principal cannot actuate directly —
`call_service` *and* `execute_script` both fail with `UnknownUser`.

Every other path trusts the `ActiveConnection.user` object captured at authentication
(`decorators.py:62`, `commands.py:355`), which survives `_users.pop()` as a strong
reference. So a removed principal retains reads, subscriptions, and **all 389
`require_admin` websocket commands** — including `fire_event`.

`fire_event` performs no service call itself. It puts an event on the bus; the
**automation** then makes the service call under the *automation's* context, which
passes the line-729 check trivially. **The automation launders the authority.**

| probe on the orphaned socket | after REMOVE | after DEACTIVATE (control) |
|---|---|---|
| `call_service` / `execute_script` | blocked, `UnknownUser` | connection closed |
| `get_states` | **19/19 entities** | connection closed |
| live `state_changed` subscription | **delivering** | connection closed |
| `config/auth/list` | **succeeds** (enumerates the household) | connection closed |
| `fire_event` → automation → actuation | **ACTUATES** | connection closed |
| new connection, same token | rejected | rejected |

**Necessity (E3.4).** Witness `W = {orphaned socket, event-triggered automation}`.
Full witness → residue. Minus socket → collapses. Minus automation → collapses.
Both load-bearing ⇒ **CRD = 2, empirically**, not by model construction.

---

## 3. Per-property outcomes

| property | outcome | evidence |
|---|---|---|
| **RC** revocation-completeness | **FALSIFIED** on all four platforms under ≥1 reading; DETERMINED-and-falsified on HA | E7.4/E7.6, Alloy probes |
| **NRT** no-residual-after-transfer | **CONTINGENT**, both directions (prior-owner retains; new owner reads history) | `NRT_A_*`, `NRT_B_*` |
| **GTB** guest-time-bounding | **CONTINGENT** on whether expiry cascades to the session it minted | `GTB_*` |
| **DNA** delegation-non-amplification | capability dimension **VERIFIED** (Tamarin, 543 steps, inductive); device dimension falsified **by construction only** | `tenantsafe_dna.spthy` |

**E4.3 — DNA per platform.** None of the four platforms exposes a user-to-user
re-delegation primitive: Google Home is admin-only, SmartThings owner-only, Home
Assistant has no user-to-user delegation, Alexa documents none. **DNA therefore holds
vacuously on all four** — the prior expectation ("DNA likely holds") is correct, but
for an uninteresting reason: there is nothing to amplify. The interesting DNA result is
structural, not per-platform: on a *total order* DNA is trivial, and amplification can
only hide in an unvalidated dimension of a multi-dimensional scope.

---

## 4. Determinacy (Definitions 5–6)

**14 DETERMINED · 3 CONTINGENT · 7 SILENT** (corrected; the original 15/3/6 was wrong).
Coding reliability **κ = 0.923**, CI [0.775, 1.000], 23/24 agreement — passes the
predeclared ≥0.70 gate. ⚠️ *Intra-rater (test-retest), same analyst; not inter-rater.*

**Two SILENT-ROBUST cells** — SmartThings/`evict` and HA/`evict` come out falsified under
*both* readings. The documentation is silent but the silence is **harmless**: the
property's truth does not depend on the undocumented choice. For SmartThings this is
stronger than a contingency claim — whichever way member-authored Routines are handled,
the removed principal's surviving trigger still reaches an automation.

---

## 5. TSMON reference monitor

The minimal correct fix: apply the provenance check the service path *already performs*
at the two paths that skip it. No new policy, no new state, no new configuration.

- **E6.3 closure:** both residues closed with a valid control — `fire_event` → `unauthorized`, entity stays off; `get_states` 19 → 0
- **E6.5 ablation:** revert TSMON ⇒ both residues **return**. The counterfactual holds
- **E6.4 cost:** **18.9 ns per decision** (dict membership), ~5 orders of magnitude below the ~1.2 ms WebSocket RTT that dominates end-to-end
- **E6.6 ablation A-4:** cascade-on-removal eliminates **100%** of both documented Google Home channels (lock passcode, ecosystem binding)

⚠️ The end-to-end latency arms were measured **across container restarts and are
unpaired**; only the microbenchmark is sound. Reported as such.

---

## 6. Scale (sampled arm — inference required)

N = 9,000 (9 platform-readings × 1,000), seed 20260822. Composed (automation-channel)
share among residues **0.449**, 95% CI [0.432, 0.465]. Mixed model converged, random
intercept on stratum, held-out accuracy 0.660.

⚠️ Fitted as a **linear probability model**, not logistic (statsmodels `mixedlm` is
linear) — a deviation from design §11.4. The `k_p` coefficient is negative, which is a
**generator artifact** (larger households make the fixed victim less likely to hold a
grant), not a finding.

---

## 7. Tool-choice result (methodological)

The design's tool split was justified by *measurement*, not preference:

| | Alloy | Tamarin |
|---|---|---|
| base model, executability workflows | **all SAT, <1 s** | **>4 min, no verdict** (twice, before and after tuning) |

The base model is a state-transition system with unbounded object creation and no
cryptographic structure, so Tamarin's constraint solving has nothing to anchor on.
Tamarin's role narrowed to DNA — the one property needing unbounded induction — where
it succeeds in 0.87 s. Shared-fragment conformance **20/20 PASS**.

**Scope escalation (E4.4):** the HA deputy residue is still SAT at scopes 6 and 8, and
`HA_sess_act` still UNSAT. No new qualitative behaviour ⇒ supports insight I5.

---

## 9. Mock-review response results (2026-08-25)

### 9.1 Operation matrix — 30 independent trials per arm
Every cell is 0/30 or 30/30; Wilson intervals [0.000, 0.114] or [0.886, 1.000].
The behaviour is structural, not intermittent.

| Operation | member/delete | member/deactiv. | admin/delete | admin/deactiv. |
|---|---|---|---|---|
| read state | **30/30** | 0/30 | **30/30** | 0/30 |
| new subscription | 0/30 | 0/30 | **30/30** | 0/30 |
| pre-existing stream | **30/30** | 0/30 | **30/30** | 0/30 |
| list users | n/a | n/a | **30/30** | 0/30 |
| direct actuation | 0/30 | 0/30 | **0/30** | 0/30 |
| script execution | n/a | n/a | 0/30 | 0/30 |
| fire event | n/a | n/a | **30/30** | 0/30 |
| induced actuation | n/a | n/a | **30/30** | 0/30 |
| **highest capability** | View | — | **Administer** | — |

Direct actuation is refused 0/30 even for a removed administrator while induced
actuation succeeds 30/30 — an independent runtime corroboration of CRD = 2.

### 9.2 Session conditions — the defect is one path
Both concurrent sockets survive deletion. A fresh socket with the old token is
refused, as is a long-lived token. Deactivation, explicit refresh-token
revocation, and new-connection authentication are all **complete**. Only removal
leaves the connection running.

### 9.3 Second runtime ecosystem — openHAB 4.3.2
Clean on the request path (401 on read, command and rule execution). **Residual
on established SSE connections in 5/5 independent trials**, and `clearSessions`
does not close them either. Home Assistant at least owns a working teardown path
that removal fails to invoke; openHAB has no equivalent remedy available.

### 9.4 Model mutation testing — the instrument discriminates
8 mutants, 15 commands, **15/15 match predicted verdicts**. M5 (session +
automation) is the only mutant reported as CRA; M1, M4 and M7 have residue and
are correctly reported at depth 1.

### 9.5 Composition depth 1–4 — depth is not a renamed conjunction
14/14. Supports of size 1, 2, 3 and 4 each constructed and machine-checked, each
with its "no smaller sufficient support" check UNSAT.

### 9.6 Scope sensitivity
17/17 verdicts identical across four scope/budget points while solver runtime
grows 4.9 s → 75.0 s. Bounded claim only: no new qualitative pattern appears
*within the tested model*.

### 9.7 Performance — no difference beyond noise
Three simultaneous instances, matched restart counts, rotated arm order; 5 runs ×
10,000 ops/arm. **All 12 defense-vs-baseline CIs overlap baseline.** Authorization
check costs **25.6 ns** amortized (the 83 ns per-op figure was 57 ns of timer).

### 9.8 Lifecycle regression — 22 tests
Defense A **22/22, 0 security and 0 functional regressions**. Baseline 20/22 with
**2 security regressions**, at exactly the two deletion assertions.

### 9.9 Residual lifetime — no time-based expiry

| Delay / event | socket | read | stream | actuation |
|---|---|---|---|---|
| pre-deletion control | 1 | 1 | 1 | 1 |
| immediately … +6 hours | 1 | 1 | 1 | 1 |
| after automation reload | 1 | 1 | 1 | 1 |
| after integration reload | 1 | 1 | 1 | 1 |
| after platform restart | **0** | **0** | **0** | **0** |

Unchanged at every delay point out to six hours. The **+30 min** row is the
informative one: access tokens carry a 30-minute lifetime and the connection
outlives the credential that opened it, so validity is established once at setup
and never revisited. Neither reload path — the two actions available from the
interface — closes it. Only a full restart does, and incidentally.

### 9.10 Automated residue finder
`tools/residue_finder.py` reproduces CRD = 2 for Home Assistant from a
declarative spec and **agrees with the Alloy verdicts on 10/10** path-level
comparisons. The cross-validation found and fixed a real gap in the tool
(self-triggering automations).

---

## 8. What would overturn this

1. **Def. 4 clause (v) under the strict reading.** The orphaned socket holds a strong
   reference to the removed user's object. Nothing *household-enumerable* names them
   (`config/auth/list` returns 3, not 4), but strictly a surviving object does. **If the
   strict reading is adopted, EXIT-A does not fire and the verdict becomes EXIT-C.**
   This is the single most consequential open question in the project.
2. **Coverage is partial.** 20-row grid, not the full 4 × 6 × 4 × 2 sweep. RC is well
   covered on `evict`; NRT/GTB/DNA are probed platform-neutrally.
3. **Inter-rater reliability is absent.** κ is test-retest by one analyst.
4. **Three cloud platforms are documented-semantics only.** Only HA reaches L3.
