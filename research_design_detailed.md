# TENANTSAFE — Detailed Technical Research Design

**Project** `prj_01M0EEDR6PYRHSPSG2VF68D7EM` · **Missions** M1 `mis_01M0EEHKZB9D1JJEBXN468C68Q` (gate, GO) → M2 `mis_01M0EEJGDZG4FMASTVWPKC0R4G` → M3 `mis_01M0EEK4N30N3M0J1Y80DE8GRE` → M4 `mis_01M0EEKTB8J2Z5XETNHVDE196M`
**Sibling** FABRICPROOF `prj_01KY1JVKHYZW6MZJ6PQKNPTHZW` (Matter protocol layer; substrate donor)
**Venue** IEEE S&P / NDSS — *chosen*, not inferred. Consequence: the mechanized calculus is the headline and the measurement study is supporting, which forces the floor upward (see §13).
**Date** 2026-08-19 · **Author** Executor, TENANTSAFE

---

## Status and discipline

**Read this paragraph before any number below.** Every quantity in this document is a **target to be measured, never a result being reported.** Nothing here has been run. The only completed work is the M1 scoop audit (`jrn_01M0EEEDBA2BKR941H551308X0`, confidence `tested`, verdict GO) and the M1 semantics-harvest feasibility judgement. Any figure that appears with a threshold attached is a predeclared success criterion, not a finding.

**Thrust structure.**
- **Act I — Thrust α (measurement + formal, THE FLOOR).** A transition calculus for household authority, mechanized, plus a *specification-determinacy instrument* that turns documentation silence into a formal quantity. Act I is the paper's floor. It stands whether or not any platform turns out to be violating anything.
- **Act II — Thrust β (hypothesis under test, THE CEILING).** That residual authority after household transitions is **compositional** — assembled from surviving objects none of which individually names the removed principal — and that this is why the fix platforms actually implement (ACL-row deletion) does not close it. Act II is a hypothesis, not a premise.
- **Thrust γ (enforcement, dependent).** A reference monitor on Home Assistant that closes whatever Act II establishes, at measured overhead.

**The gate.** Stage 3 (§11) is the single designated experiment. It resolves whether shipping platforms are *wrong* (falsifiable, with traces) or merely *silent* (contingent). **Build nothing below the gate until it resolves** — specifically, do not implement the reference monitor (Thrust γ / M3), because *what it must enforce* is determined by which exit fires.

**Hard resource constraint, binding on the whole design.** No physical hardware of any kind. No purchased devices, no hubs, no radios. No APK analysis, no AndroZoo, no companion-app decompilation — that dependency was deliberately designed out at project creation (`jrn_01M0EEFTCZ23XXG86W8VR6799E`) because it is the exact blocker that killed P12 BINDFLAW. Compute is one MacBook Pro M4, 24 GB, running Alloy, Tamarin, TLA+ and Docker natively on ARM macOS. Every stage below is executable inside that envelope; §7-C9 states what this costs us.

**Predeclaration.** The property catalog (§9), the severity classes (§9), the persistence classes (§9), the statistical contrasts (§11), and every success threshold are fixed **before** Stage 3 runs. This is deliberate: predeclared so "damage" is never defined after the fact, and so an EXIT-B outcome cannot be quietly relabelled as EXIT-A once traces are in hand.

---

## Spine (one line)

**Smart-home access control has been formalized as a predicate over an instant; the harms are all transitions, so we formalize authority as a calculus over the events that change who the principals are, and machine-check whether authority is genuinely extinguished when a platform says it has been.**

## Spine (thesis)

TENANTSAFE claims, jointly:

**(A)** Household authority admits a formal calculus whose objects are *transition events* — `grant`, `delegate`, `expire`, `evict`, `transfer-ownership`, `factory-reset` — rather than a policy evaluated at an instant; and within that calculus the central object is the **authority residue**, the set of capabilities a principal may no longer exercise by policy but can still effect along some reachable trace. Revocation-completeness is exactly the emptiness of that residue, a statement no instant-based model can even express because it has no post-state.

**(B)** Residual authority in real household platforms is typically **composed**: it arises from the interaction of two or more surviving objects, none of which individually names the removed principal as an authorized subject. If true, this explains why the obvious remedy — delete every ACL row naming the evicted principal, which is both what a competent engineer does and what platforms document themselves as doing — is insufficient by construction rather than by oversight.

**(C)** Where documentation does not determine the outcome of a transition, that silence is itself formally tractable: model both readings, and the set of properties whose truth *flips* between them is a measurable quantity. A user who cannot determine whether an abuser retains access is materially unsafe; we make the size of that indeterminacy a number rather than a complaint.

**Structural analogy, used for shape only.** Claim (B) has the *shape* of return-oriented programming: authority is assembled from fragments, none of which was individually intended to confer it, and the assembly is what carries the effect. **We are not claiming** code reuse, gadget chaining, control-flow hijacking, or any mechanism of ROP. The analogy is borrowed for one property alone — that the dangerous object is a *composition* and therefore invisible to any defense that inspects fragments one at a time. Likewise the confused-deputy shape in §10 SC-1: we borrow the shape (an agent acting with authority not its own), not Hardy's setting.

---

## 1. Problem statement and formal model

### 1.1 Informal problem

Households change. Partners separate, roommates depart, guests overstay, homes are sold, children age into and out of supervision, landlords rotate tenants. Every documented harm in the multi-user smart-home literature is anchored to one of these moments: the ex-partner who still controls the thermostat, the prior owner who still sees the camera, the guest whose four-hour window never closed. Yet every incumbent access-control system for the smart home — KRATOS, Fluid-IoT, attribute-based schemes, ephemeral-authorization work — answers a question about a *moment*: given these people and these devices right now, who may do what, and how do we reconcile conflicting demands. None answers what must be true *after* the household changes. Meanwhile the formal-methods literature that a reviewer will surface under "formal verification smart home" verifies **authentication** — session keys, mutual identification, AVISPA and Real-or-Random and BAN-logic proofs that the right principal is *identified*. Being identified and being *authorized* are different questions, and only the second one is about what an ex-partner can still do.

### 1.2 State spaces and the objects that move

Let:

- `P` — finite set of **principals**, `p ∈ P`. Roles drawn from `R = {owner, partner, roommate, guest, child, landlord, prior_owner, new_owner, removed}`.
- `D` — finite set of **devices/resources**, `d ∈ D`.
- `C` — finite set of atomic **capabilities**, `c ∈ C = {view_state, actuate, view_history, view_stream, configure, manage_members, unlock, factory_reset, grant_authority}`.
- `T` — **time**, a finite totally ordered set of epochs `t₀ < t₁ < … < t_max`. Time is explicit and non-negotiable: guest-time-bounding is meaningless without it.
- `Θ` — **surviving objects**, the artifacts that persist across a transition and can carry authority: grant rows, live session tokens, authored automations, trigger entities, secondary-ecosystem bindings, cached local-path credentials, stored history.

A **grant** is
```
g = (issuer, subject, device, capability, [t_start, t_end], δ)  ∈  P × P × D × C × T × T × ℕ
```
where `δ` is the residual **re-delegation depth budget**. `δ = 0` means the grant may not be re-delegated.

A **household configuration** at epoch `t` is
```
H_t = ⟨ P_t , D_t , G_t , O_t , A_t , Σ_t , B_t ⟩
```
with `G_t ⊆` grants, `O_t : D → P` the ownership map, `A_t` the set of authored automations (each a triple `⟨author, trigger, effect⟩`), `Σ_t` the set of live session tokens `⟨subject, scope, expiry⟩`, and `B_t` the set of secondary-ecosystem bindings `⟨device, ecosystem, admin⟩`.

A **transition event** is a partial function on configurations,
```
e : H  ⇀  H',       e ∈ E = {grant, delegate, expire, evict, transfer_ownership, factory_reset}
```
Each `e` is instantiated *per platform* from documented semantics (§11 Stage 2). This is the whole point: `evict` is not one function, it is four different functions — one per platform — and where documentation is silent it is a *pair* of functions (§1.6).

### 1.3 The actor as a constrained function

The adversarial principal is not omnipotent. Model `p` as a function
```
𝒜_p : H × K → Actions*
```
constrained by an explicit **feasibility set**, and *only* by it:

1. `p` may issue an action only if `p` holds a credential in `Σ` or a grant in `G` that the platform's own dispatch would accept — `p` does not forge.
2. `p` may exercise a local-network path only if `retains_local_network = true` in the capability record.
3. `p` may act through a secondary ecosystem only if `retains_secondary_ecosystem_binding = true`.
4. `p` may trigger an automation only via a trigger entity that persists in `A_t`'s trigger domain.
5. `p` is bounded by an **action budget** `β` (number of effect-attempts) and an **epoch budget** `τ` (wall-clock epochs available).
6. `p` does **not** have: physical presence, credential coercion, social engineering, or platform-implementation exploits. Those are out of scope (§2.4) and their exclusion is what keeps the claim about *authority*, not about attack surface generally.

Anything not in the capability record (§2.3) was not assumed.

### 1.4 The distinguishing formal device — the authority residue

This is the definition that makes the novel claim checkable, and it is the technical core of the paper.

Write `Auth(p, d, c, H)` for the platform's own authorization predicate at configuration `H`, and `Effect(p, d, c) ∈ τ` for "trace `τ` contains `p` successfully effecting capability `c` on device `d`".

> **Definition 1 (Authority residue).** For a principal `p`, transition event `e`, and configuration `H`, let `H' = e(H)`. The **residue** is
> ```
> Res(p, e, H)  =  { (d,c) ∈ D×C  :  ¬Auth(p,d,c,H')  ∧  ∃ τ ∈ Traces(H', 𝒜_p, β, τ_max) . Effect(p,d,c) ∈ τ }
> ```

The residue is the gap between *de-authorized by policy* and *de-authorized in fact*. Every documented harm in the literature is an instance of `Res ≠ ∅`.

> **Definition 2 (Revocation-completeness).** `RC(p,e,H) ⟺ Res(p,e,H) = ∅`.

Note what Definition 1 buys. Instant-based models express `Auth(p,d,c,H)` and nothing more; they have no `e` and no `H'`, so they cannot state Definition 2 at all — not because they answer it wrongly, but because the sentence does not typecheck in their formalism. That is the precise sense in which this is a different object of study rather than a better solution to the same one.

### 1.5 The novel mechanism, formalized — Composed Residual Authority

Definition 1 alone is satisfied by a plain bug: a platform forgets to delete a grant row, the row still names `p`, `p` acts. That is a defect report, not a phenomenon. The claim in spine part (B) is stronger and needs its own statement.

> **Definition 3 (Composition depth).** For `(d,c) ∈ Res(p,e,H)`, let `Wit(d,c) ⊆ Θ_{H'}` range over minimal sets of surviving objects such that removing all of `Wit` from `H'` yields `(d,c) ∉ Res`. Define
> ```
> CRD(d,c)  =  min { |W| : W ∈ Wit(d,c) }
> ```

> **Definition 4 (Composed Residual Authority, CRA).** `CRA` holds iff
> ```
> ∃ H, ∃ e ∈ E, ∃ p ∈ P, ∃ (d,c) ∈ D×C  such that
>   (i)   Auth(p,d,c,H)                              — p was authorized before
>   (ii)  ¬Auth(p,d,c,e(H))                          — policy denies p after
>   (iii) (d,c) ∈ Res(p,e,H)                         — p can still effect it
>   (iv)  CRD(d,c) ≥ 2                               — no single surviving object suffices
>   (v)   ∀ θ ∈ Θ_{e(H)} . subject(θ) ≠ p            — no surviving object names p as subject
> ```

Clause **(iv)** is the anti-triviality clause: it forbids the "they forgot to delete the row" reading. Clause **(v)** is the sharper one: it says the ACL is *clean* — an auditor inspecting every surviving object for the evicted principal's name finds nothing, and the authority is there anyway. Together (iv)+(v) are what make CRA a phenomenon rather than a bug class, and they are what make ACL-row-deletion (baseline B1, §11.2) insufficient by construction.

**`CRA` is the ceiling hypothesis. It is under test, not assumed.** If Stage 3 finds only `CRD = 1` residues, spine (B) is false as stated and the gate fires EXIT-B or EXIT-C (§13).

### 1.6 Documentation silence, formalized

Platforms frequently do not say what `e` does. Rather than guess, instantiate both.

> **Definition 5 (Specification determinacy).** For a cell `(platform π, transition e, property φ)`, `SPEC(π,e,φ) ∈ {DETERMINED, CONTINGENT, SILENT-ROBUST}`:
> - **DETERMINED** — documented semantics fix `e` uniquely on the state relevant to `φ`.
> - **SILENT-ROBUST** — documentation is silent, but under *both* plausible readings `e_A, e_B`, `φ` has the same truth value. Silence is harmless here.
> - **CONTINGENT** — documentation is silent and `φ(e_A(H)) ≠ φ(e_B(H))`. The property's truth depends on a choice no user can observe.

> **Definition 6 (Contingency span).** `CONT(π) = |{ (e,φ) : SPEC(π,e,φ) = CONTINGENT }|`.

`CONT` is the measurement study's headline number, and it is a *formal* quantity, not a survey result: each CONTINGENT cell is certified by two mechanized models and a property that provably differs between them. This is why Act I survives at IEEE S&P even under EXIT-C — it is a theorem about the documentation, not a table of opinions about it.

### 1.7 The metric instrument

Six named metrics. Each is defined here before any use in §10 or §11.

| Metric | Definition | Range | Instrumented by |
|---|---|---|---|
| **RRC** — Residual Reachability Count | `\|Res(p,e,H)\|` | ℕ | A3 |
| **CRD** — Composition Depth | Definition 3 | ℕ ∪ {∞}; `∞` if `Res = ∅` | A4 |
| **SPEC** — Specification Determinacy | Definition 5 | ternary | A6 |
| **CONT** — Contingency Span | Definition 6 | ℕ | A6 |
| **TTE** — Time-to-Extinction | `sup{ t − t_end : ∃τ. Effect(p,d,c) at epoch t }`, for a grant ending at `t_end` | epochs ∪ {∞} | A9 |
| **MO** — Monitor Overhead | added wall-clock latency per authorization decision, median and p99 | ms | A8 harness |

**Conditionals that localize the failure.** The metrics are not independent; their joint values say *where* something broke, which is what makes them an instrument rather than a scoreboard:

```
Res = ∅ under both readings          → φ HOLDS ROBUSTLY (report even though negative)
Res = ∅ under e_A, Res ≠ ∅ under e_B → CONTINGENT; increment CONT; severity from the worse reading
Res ≠ ∅ ∧ SPEC = DETERMINED ∧ CRD = 1 → IMPLEMENTATION-DEFECT class; report, not flagship
Res ≠ ∅ ∧ SPEC = DETERMINED ∧ CRD ≥ 2 → CRA; flagship; run necessity test A5 before claiming
Res ≠ ∅ ∧ executability lemma failed  → VACUOUS; model is unfaithful; NOT a finding (see C3)
TTE = ∞ with t_end finite             → guest-time-bounding falsified
```

**Breakdown of misses.** A property that is not proved has four meaningfully different fates, and conflating them is the standard way formal-methods papers overclaim:
- **FALSIFIED** — a counterexample trace exists. A finding.
- **CONTINGENT** — truth differs across readings. A finding, of a different kind.
- **UNRESOLVED-BUDGET** — tool exhausted scope/time without verdict. **Not a finding.** Report the scope reached.
- **VACUOUS** — executability lemmas fail, so the model admits no legitimate workflow and proves everything trivially. **Not a finding.** A bug in us.

### 1.8 Tractability — naming the hard problem

The general safety question here is **undecidable**. The Harrison–Ruzzo–Ullman result (1976) establishes that safety in the general access-matrix model with unrestricted commands is undecidable; our model is strictly richer (delegation depth, time, automations as standing delegations), so it inherits that. We do not step around this.

> **Proposition 1 (Bounded decidability).** Fix `|P| ≤ k_P`, `|D| ≤ k_D`, `δ ≤ δ_max`, `|T| ≤ k_T`, action budget `β < ∞`. Then `H` ranges over a finite set, `Traces(H', 𝒜_p, β, τ_max)` is finite, and `Res(p,e,H)` is computable by exhaustive enumeration. The decision problem "is `(d,c) ∈ Res`?" is PSPACE-complete under succinct representation of the configuration, by the standard reduction from bounded reachability in a succinctly-presented transition system.

*Why this bound is not a cheat.* Every documented harm scenario in the multi-user smart-home literature involves **≤ 5 principals and ≤ 4 devices** — separations, roommate departures, resales, guest visits. Jackson's small-scope hypothesis is unusually well-founded in this domain: the counterexamples we care about are small because *households* are small. This is the substantive methodological argument that the usual "formal methods don't scale" objection does not bite here, and it is Insight 5 (§4).

**Consequently:** exact exhaustive methods at small scale (Alloy, `k_P ≤ 6`, `k_D ≤ 4`, `δ_max ≤ 3`), inductive unbounded proof where the property admits an invariant (Tamarin, reusing FABRICPROOF's ACL substrate), and heuristic sampled search only beyond exhaustive scope (§5 A7, §11 Stage 5). Tool choice is justified by property structure in §5.0 — not by familiarity, which M2/T2 explicitly forbids.

### 1.9 Notation summary

| Symbol | Meaning |
|---|---|
| `P, D, C, T, R` | principals, devices, capabilities, epochs, roles |
| `Θ` | surviving objects (grants, tokens, automations, triggers, bindings, history) |
| `g = (i,s,d,c,[t₀,t₁],δ)` | grant: issuer, subject, device, capability, validity window, re-delegation depth |
| `H_t = ⟨P,D,G,O,A,Σ,B⟩` | household configuration at epoch `t` |
| `A` | authored automations `⟨author, trigger, effect⟩` |
| `Σ` | live session tokens `⟨subject, scope, expiry⟩` |
| `B` | secondary-ecosystem bindings `⟨device, ecosystem, admin⟩` |
| `e ∈ E` | transition event; platform-instantiated |
| `e_A, e_B` | the two readings of a silent transition |
| `Auth(p,d,c,H)` | platform's own authorization predicate |
| `Res(p,e,H)` | authority residue (Def. 1) |
| `CRD` | composition depth (Def. 3) |
| `CRA` | composed residual authority (Def. 4) |
| `SPEC, CONT` | specification determinacy, contingency span (Defs. 5–6) |
| `β, τ_max` | action budget, epoch budget |
| `π` | platform ∈ {google_home, alexa, smartthings, home_assistant} |
| `φ` | property ∈ {RC, NRT, DNA, GTB} (§9) |

---

## 2. System model in the notation

### 2.1 Components

```
┌─ Vendor cloud (π) ──────────────────────────┐
│  household record, member list, grant store │   ← modeled from L0/L1 documentation only
│  automation engine, token service           │
└──────────────┬──────────────────────────────┘
               │ documented API semantics
┌──────────────▼──────────────┐   ┌──────────────────────────┐
│  Hub / controller           │   │  Secondary ecosystem π'  │  ← multi-admin, B
│  (Home Assistant, Docker)   │   │  (independent grant store)│
└──────────────┬──────────────┘   └──────────────────────────┘
               │ integration boundary  ← reference monitor sits HERE (Thrust γ)
┌──────────────▼──────────────────────────────┐
│  Devices (VIRTUAL ONLY — demo/template/MQTT)│   ← no physical hardware, ever
└─────────────────────────────────────────────┘
```

The reference monitor's position at the integration boundary is a design commitment with consequences: it can mediate everything HA dispatches and **nothing** the vendor cloud dispatches directly to a device. That is stated as a non-guarantee in §5.9, not buried.

### 2.2 Observability lattice

Every semantic fact carries the level it was obtained at. Claims derived at a lower level are weaker, and the paper must never silently promote one.

```
L3  IMPLEMENTED BEHAVIOR      — what the platform actually does
      └─ NOT OBSERVABLE in this project for π ∈ {google_home, alexa, smartthings}.
         UPPER BOUND ONLY. Named as future work (§7-C2).
         Exception: for π = home_assistant, L2 ≈ L3 because the source IS the implementation
         and we can run it. This is the single confirmation anchor (Stage 7).
L2  OPEN SOURCE / SPEC        — Home Assistant source; Matter spec; FABRICPROOF ACL model
L1  DEVELOPER DOCUMENTATION   — published API/developer docs, precise but partial
L0  PUBLIC USER DOCUMENTATION — help-center articles; what a user could actually read
```

Each algorithm consumes only what it is authorized to see. `A6` (dual-modeling) runs at L0∪L1 for the three cloud platforms and at L2 for Home Assistant. `A8` (monitor) runs at L2 exclusively. No algorithm consumes L3 for a cloud platform, because we do not have it — and the design's honesty depends on never pretending otherwise.

### 2.3 Capability record schema

Shipped with **every** result. Anything absent from the record was not assumed.

```json
{
  "record_id": "tsafe-<platform>-<transition>-<property>-<reading>-<nnn>",
  "platform": "google_home | alexa | smartthings | home_assistant",
  "doc_snapshot": {
    "urls": ["..."],
    "retrieved_utc": "2026-08-19T00:00:00Z",
    "sha256": ["..."],
    "archive_url": ["https://web.archive.org/..."]
  },
  "observability_level": "L0 | L1 | L2 | L3",
  "principal": {
    "role_before": "owner|partner|roommate|guest|child|landlord|prior_owner",
    "role_after":  "removed|guest|new_owner|unchanged",
    "retains_physical_presence":            false,
    "retains_local_network":                true,
    "retains_secondary_ecosystem_binding":  false,
    "retains_authored_automations":         true,
    "retains_live_session_token":           true,
    "retains_trigger_entity":               true
  },
  "transition": "grant|delegate|expire|evict|transfer_ownership|factory_reset",
  "knowledge": {
    "knows_device_ids": true,
    "knows_household_credentials": false,
    "knows_other_member_credentials": false
  },
  "budget": { "actions_beta": 100, "epochs_tau": 10 },
  "semantic_reading": "documented | reading_A | reading_B",
  "reading_justification": "docs do not state whether member removal cascades to grants ISSUED BY that member",
  "metrics": { "RRC": null, "CRD": null, "SPEC": null, "TTE": null },
  "verdict": "HOLDS | FALSIFIED | CONTINGENT | UNRESOLVED-BUDGET | VACUOUS",
  "necessity_test": { "run": false, "collapsed_on_removal_of": [] }
}
```

### 2.4 Trust assumptions, and what is *not* silently included

**Assumed:** the platform's own dispatch is faithful to its documentation at the modeled level; cryptography is sound (we verify authority, not identification — that is the AVISPA literature's job and we cite it rather than redo it); the adversary does not forge credentials.

**NOT assumed, and therefore NOT covered — stated here so no reader imports them:**
- Physical access to devices or to the premises.
- Credential coercion — the abuser who demands the survivor's password. This is a real and common IPV vector that no access-control calculus addresses.
- Social engineering of other household members or of vendor support.
- Implementation vulnerabilities (memory safety, injection, authentication bypass).
- Radio-layer or physical-layer attacks.
- **The case where the abuser is the account owner.** TENANTSAFE helps the principal who *has* the authority to evict. It does not help the principal whose abuser holds owner. This is the single most important limitation of the entire project and it belongs in the abstract, not the appendix.

---

## 3. Motivation, state of the art, and gap

Condensed from the M1 scoop audit (`jrn_01M0EEEDBA2BKR941H551308X0`, verdict GO).

**Line 1 — Multi-user smart-home access control.** Zeng & Roesner (USENIX Security 2019) established the empirical problem through design exploration and an in-home study. KRATOS (Sikder, Babun, Celik, Acar, Aksu, McDaniel, Kirda, Uluagac) provides multi-user multi-device-aware access control with a policy manager that *negotiates* between users to resolve conflicting demands, evaluated on 309 policies including 213 demand conflicts. Fluid-IoT (CHI 2024) delivers fine-grained access in shared environments via multi-user UI distribution. Goyal, Liu & Sural (ACM CPSS 2022) apply ABAC. Lux (IoTDI 2021) gives ephemeral authorization for display-limited devices. Pattnaik et al. (CSCW 2024) study perceptions in shared homes.
*What they do:* determine and reconcile authority among co-present principals.
*What they do not do:* define, let alone verify, what must hold **after** a principal ceases to be a household member. None has an `e`; none has an `H'`; none can state Definition 2.

**Line 2 — Formal methods in smart homes, aimed at a different object.** A substantial body verifies smart-home **authentication**: AVISPA-checked schemes, Real-or-Random proofs, BAN-logic analyses, PRNU-based remote user authentication, home-registration access schemes.
*What they do:* prove session-key establishment and mutual authentication — the right principal is **identified**.
*What they do not do:* prove anything about **authority** — what an identified principal may then do, how it narrows on delegation, whether it is extinguished on revocation.
**This disambiguation goes in §2 of the paper, early and explicit** (M1/T2 deliverable), because a reviewer skimming "formal verification + smart home" will surface these and assume overlap. Identification ≠ authority is the single sentence that must land.

**Line 3 — Protocol-layer revocation.** Matter 1.4.2 adds Certificate Revocation Lists so ecosystems can revoke compromised Device Attestation Certificates. This is *device* attestation revocation — is this device genuine — not *user* authority revocation. Useful evidence that the ecosystem is addressing revocation one layer below the one where households live. Sibling project FABRICPROOF models Matter fabrics, operational certificates, ACL entries, factory reset and resale at this layer; its Tamarin ACL model is a direct input here (§5.0) and the two papers cite each other. Boundary recorded as decision D3: **FABRICPROOF proves things about fabrics and certificates; TENANTSAFE proves things about principals, roles and delegation across household events.**

**Line 4 — IPV and technology.** An active community documenting technology-facilitated abuse, including smart-home abuse, largely through qualitative and clinical-intervention work. Highly relevant to threat realism and to the safe-exit templates (§6 Thrust γ), and a source of external validity we should not fake — but it does not formalize revocation.

### The N-dimension intersection

No prior work holds these **five** jointly, and the paper's positioning is exactly this conjunction:

1. **Transitions, not instants** — the object of study is `e`, not `Auth(·,·,·,H)`.
2. **Authority, not identification** — what a principal may do, not whether they are who they claim.
3. **Machine-checked**, not designed-and-evaluated-by-user-study.
4. **Instantiated against shipping platform semantics**, not against an idealized model of the author's own design.
5. **Silence treated as a formal object** (Def. 5–6), not as a gap to be filled by assumption.

Lines 1 and 3 hold #1 partially at a layer below humans. Line 2 holds #3 but not #1 or #2. Line 1 holds #4 but not #3. Nothing holds #5 at all.

---

## 4. Insight

Five, each a mechanism rather than a motivation.

**I1 — Deleting the row is not deleting the authority.** Authority is extinguished only when no reachable trace realizes the capability, not when the ACL entry naming the principal disappears. The gap between these two predicates is `Res`, and that gap is the entire object of study. Platforms implement and document the first and claim the second.

**I2 — Residual authority is compositional, which is why the obvious fix fails.** Residue typically arises from the *interaction* of surviving objects, none of which individually names the removed principal. A defense that inspects artifacts one at a time — which is what row-deletion, and every audit UI built on it, does — is structurally incapable of seeing it. This is the ceiling hypothesis and the reason B1 (§11.2) is the baseline that matters.

**I3 — Automations are deputies that outlive their authors.** A rule authored by `p`, executing with *household* authority, triggered by an entity bound to `p`, is a standing delegation that appears in no ACL and names `p` nowhere in the authorization path. Removing `p` from the member list does not remove `p` from the trigger domain. This is the cleanest instance of I2 and it is the flagship scenario SC-1.

**I4 — Silence is measurable.** Where documentation does not determine `e`, instantiate both readings and take the *difference*. The set of properties whose truth flips is a formal quantity (`CONT`), certified by two mechanized models. This converts "the docs are vague" from a complaint into a theorem, and it is what lets Act I stand at a top-tier security venue rather than reading as a documentation survey.

**I5 — Households are small, so exhaustive analysis is genuinely in range.** Every documented harm in Line 1 involves ≤ 5 principals and ≤ 4 devices. Small-scope exhaustive enumeration is therefore not a concession to tractability but an *adequate* method for this domain — which disarms the standard scalability objection rather than deflecting it.

---

## 5. Proposed system and algorithms

### 5.0 Tool choice, justified by property structure

M2/T2 requires the justification be structural, not habitual. It is:

| Property | Structure | Tool | Why |
|---|---|---|---|
| **DNA** delegation-non-amplification | safety invariant over **unbounded** delegation chains | **Tamarin** | needs induction over chain length; finite scope cannot establish it. Reuses FABRICPROOF's ACL substrate directly. |
| **RC** revocation-completeness | **bounded reachability** over rich heterogeneous state (`G,A,Σ,B`) | **Alloy** | counterexample-rich, fast, relational state is native; small-scope hypothesis well-founded here (I5). Falsification speed is what the gate needs. |
| **NRT** no-residual-access-after-transfer | bounded reachability, **bidirectional** | **Alloy** | same; both directions expressed as two predicates over one model. |
| **GTB** guest-time-bounding | **timed** reachability with explicit clock | **TLA+ / TLC** | Tamarin's ordering is too weak for real-time bounds; TLC handles explicit clocks cleanly. Fallback: Alloy with epochs as an ordered signature if TLC state-space proves unmanageable. |

**Dual encoding is a deliberate cost.** Alloy and Tamarin models of the same system can drift apart and silently verify different things. Mitigation C7 (§7) makes cross-encoding consistency an explicit Stage 0 obligation, not an assumption.

### 5.1 Components

- **CALC** — the calculus (§1), as a platform-parametric spec.
- **INST(π)** — per-platform instantiation of `E` from the harvested corpus, with dual readings where silent.
- **RESOLVE** — the residue engine (A1–A4).
- **DUAL** — the determinacy instrument (A6).
- **TSMON** — the reference monitor on Home Assistant (A8).
- **CAPREC** — capability-record emitter, wired into every algorithm's output path.

### 5.2 Algorithm 1 — `EFFECT` (deterministic execution primitive)

Everything calls this. It is the only place platform semantics enter.

```
A1  EFFECT(p, d, c, H, π) -> bool
 1  # direct grant path
 2  if ∃ g ∈ H.G : g.subject = p ∧ g.device = d ∧ g.capability = c
 3        ∧ now(H) ∈ [g.t_start, g.t_end]                      : return TRUE
 4  # live-session path — token outlives the grant that minted it
 5  if ∃ σ ∈ H.Σ : σ.subject = p ∧ (d,c) ∈ σ.scope
 6        ∧ now(H) < σ.expiry                                   : return TRUE
 7  # deputy-automation path — p triggers, household authority executes
 8  if ∃ a ∈ H.A : a.effect = (d,c)
 9        ∧ TRIGGERABLE_BY(a.trigger, p, H)
10        ∧ AUTHORIZED(a.author_authority, d, c, H)              : return TRUE
11  # secondary-ecosystem path — multi-admin binding
12  if ∃ b ∈ H.B : b.device = d ∧ b.admin = p
13        ∧ π'_DISPATCHES(b.ecosystem, d, c)                     : return TRUE
14  # local-path bypass — cloud ACL gone, local credential persists
15  if RETAINS_LOCAL_NETWORK(p) ∧ LOCAL_DISPATCH(π, d, c)        : return TRUE
16  return FALSE
```

Lines 7–10 are I3 and are where SC-1 lives. Line 10 is the confused-deputy shape: authorization is checked against the *automation's* authority, never against `p`.

### 5.3 Algorithm 2 — `REACH` (exact bounded enumeration)

```
A2  REACH(H', 𝒜_p, β, τ_max) -> set of traces
 1  frontier ← {⟨H', [], 0, 0⟩}                       # config, trace, actions, epoch
 2  seen ← ∅ ; out ← ∅
 3  while frontier ≠ ∅:
 4      ⟨H, τ, n, t⟩ ← pop(frontier)
 5      if canon(H,t) ∈ seen: continue
 6      seen ← seen ∪ {canon(H,t)}
 7      out ← out ∪ {τ}
 8      if n ≥ β or t ≥ τ_max: continue
 9      for each action α feasible for p under §1.3 constraints:
10          H₂ ← apply(H, α)
11          frontier ← frontier ∪ {⟨H₂, τ·α, n+1, t⟩}
12      frontier ← frontier ∪ {⟨tick(H), τ, n, t+1⟩}   # epoch advance: expiries fire
13  return out
```

Line 12 is not optional — without an epoch-advance successor, `GTB` is unfalsifiable because nothing ever expires. Implemented natively by Alloy's bounded scope; A2 is the reference semantics the Alloy encoding must agree with (C7).

### 5.4 Algorithm 3 — `RESIDUE`

```
A3  RESIDUE(p, e, H, π) -> set of (d,c)
 1  H' ← e(H)
 2  R ← ∅
 3  for each (d,c) ∈ D × C:
 4      if AUTH(p,d,c,H',π): continue          # still authorized by policy — not residue
 5      for each τ ∈ REACH(H', 𝒜_p, β, τ_max):
 6          if ∃ prefix of τ ending in EFFECT(p,d,c,·,π) = TRUE:
 7              R ← R ∪ {(d,c)} ; break
 8  return R                                    # RRC = |R|
```

### 5.5 Algorithm 4 — `MINDEPTH` (the CRA detector)

```
A4  MINDEPTH(p, e, H, π, (d,c)) -> int ∪ {∞}
 1  H' ← e(H)
 2  Θ ← SURVIVING_OBJECTS(H')                       # grants, tokens, automations, triggers, bindings
 3  if (d,c) ∉ RESIDUE(p,e,H,π): return ∞
 4  for k = 1 to |Θ|:                                # ascending: find the MINIMAL witness
 5      for each W ⊆ Θ with |W| = k:
 6          H'' ← H' \ W
 7          if (d,c) ∉ RESIDUE_AT(p, H'', π):        # removing W kills the residue
 8              if k ≥ 2 and ∀θ ∈ Θ. subject(θ) ≠ p: # clauses (iv) and (v) of Def. 4
 9                  emit CRA_CANDIDATE(p,e,H,d,c,W)
10              return k
11  return ∞
```

Line 8 enforces Definition 4 clauses (iv) and (v) *in code*, so a CRA claim cannot be made by narrative. Subset enumeration is exponential in `|Θ|`; bounded by `|Θ| ≤ 12` at exhaustive scope, and by A7's heuristic beyond it.

### 5.6 Algorithm 5 — `NECESSITY` (anti-triviality)

Required before any CRA claim is published.

```
A5  NECESSITY(p, e, H, π, (d,c), W) -> {PASS, FAIL}
 1  # counterfactual necessity: EVERY member of the witness must be load-bearing
 2  for each θ ∈ W:
 3      H'' ← e(H) \ {θ}
 4      if (d,c) ∈ RESIDUE_AT(p, H'', π):
 5          return FAIL                              # θ was not necessary; true depth < |W|
 6  # matched-budget control: a single-object adversary with the SAME budget must fail
 7  for each θ ∈ SURVIVING_OBJECTS(e(H)):
 8      if REACHABLE_USING_ONLY(p, {θ}, d, c, β, τ_max):
 9          return FAIL                              # one object sufficed; not composed
10  return PASS
```

**Matched budget.** Line 7–9 gives the single-object adversary the *identical* action budget `β` and epoch budget `τ_max` as the composed adversary. **The headline budget is action-matched (`β`), not wall-clock-matched.** Reason: the claim in spine (B) is about *structure* — that no single surviving object confers the authority — not about effort. Wall-clock matching would let a reviewer object that the composed result merely spent more time; action matching removes that reading, and is the stricter control because it caps exactly the resource the adversary spends.

### 5.7 Algorithm 6 — `DUALMODEL` (the determinacy instrument)

```
A6  DUALMODEL(π, e, φ, corpus) -> (SPEC verdict, contribution to CONT)
 1  ⟨determined, e_doc⟩ ← EXTRACT_SEMANTICS(corpus, π, e)   # two independent coders, §11 Stage 1
 2  if determined:
 3      return ⟨DETERMINED, 0⟩ with truth φ(e_doc)
 4  ⟨e_A, e_B⟩ ← PLAUSIBLE_READINGS(corpus, π, e)            # e.g. cascade vs no-cascade on removal
 5  v_A ← CHECK(φ, e_A) ; v_B ← CHECK(φ, e_B)
 6  if v_A = v_B: return ⟨SILENT-ROBUST, 0⟩                  # silence is harmless here
 7  emit CONTINGENCY_CERT(π, e, φ, e_A, e_B, v_A, v_B)       # the formal artifact behind Def. 5
 8  return ⟨CONTINGENT, 1⟩
```

Line 4 is bounded to **exactly two** readings per transition, chosen as the two a competent engineer would most plausibly implement, and justified in the capability record's `reading_justification`. Readings are enumerated *per transition*, not globally — otherwise `n` silent cells give `2ⁿ` global models (mitigation C6).

### 5.8 Algorithm 7 — `SCALESEARCH` (heuristic, beyond exhaustive scope)

```
A7  SCALESEARCH(π, k_P, k_D, N, seed) -> sampled residue statistics
 1  rng ← seed                                       # recorded; every run reproducible
 2  results ← []
 3  for i = 1 to N:
 4      H ← GENERATE_HOUSEHOLD(k_P, k_D, rng)        # stratified by role mix and delegation depth
 5      e ← SAMPLE_TRANSITION(E, rng)
 6      R ← GREEDY_RESIDUE(p, e, H, π, depth_cap=3)  # best-first on EFFECT-path count
 7      results.append(⟨RRC=|R|, CRD=MINDEPTH_APPROX(R), platform=π, scenario=id(H)⟩)
 8  return results                                    # sampled ⇒ needs statistics (§11.4)
```

A7's outputs are **sampled and therefore require inference** (§11.4). A2/A3 outputs at exhaustive scope are **exact and require none** — the distinction is maintained rigidly, because it is the usual place formal-methods evaluations quietly mix the two.

### 5.9 Algorithm 8 — `TSMON` (the reference monitor) and its guarantee

```
A8  TSMON_DECIDE(p, d, c, H, calculus) -> {ALLOW, DENY, DENY-RESIDUAL}
 1  if ¬AUTH(p,d,c,H): return DENY                          # ordinary policy denial
 2  # residual checks — the part no platform does today
 3  if ∃ ev ∈ H.transition_log : ev.removed = p
 4        ∧ ev.epoch < now(H): return DENY-RESIDUAL          # evicted: deny regardless of path
 5  if VIA_AUTOMATION(p,d,c,H):
 6      a ← the automation ; if AUTHOR(a) ∈ REMOVED(H): return DENY-RESIDUAL
 7  if VIA_TOKEN(p,d,c,H):
 8      σ ← the token ; if MINTING_GRANT(σ) ∉ H.G: return DENY-RESIDUAL
 9  if VIA_DELEGATION_CHAIN(p,d,c,H):
10      if ∃ link in chain whose issuer ∈ REMOVED(H): return DENY-RESIDUAL
11      if DEPTH(chain) > δ_max or WIDENS(chain): return DENY-RESIDUAL   # DNA enforcement
12  return ALLOW
```

Lines 5–10 are the enforcement counterpart of the CRA hypothesis: the monitor closes residue by tracking *provenance* of authority (who minted this token, who authored this automation, who issued each link) rather than by inspecting the ACL row. That is the direct engineering consequence of I2.

**Informal guarantee.** If (i) every authorization decision for devices exposed to Home Assistant passes through `A8`, (ii) the transition log is append-only and complete, and (iii) the calculus instance is the verified one from Stage 4, then for any principal `p` removed at epoch `t`, no capability is effected by `p` at any epoch `> t` through the grant, token, automation, or delegation-chain paths of `A1` — i.e. `Res(p, evict, H) ∩ HA-mediated = ∅`.

**Non-guarantees — what this explicitly does NOT cover.** A guarantee list without this is marketing.
1. **Vendor-cloud-direct dispatch.** If the vendor cloud actuates a device without transiting HA, `A8` never sees it. Google Home and Alexa both do this. The monitor is local; the residue may not be.
2. **Implemented behavior.** The guarantee is relative to *documented* semantics for the three cloud platforms (§13 validity).
3. **The local-path bypass of `A1` line 15**, where a credential is honoured below the integration boundary.
4. **Devices not exposed to HA at all.**
5. **Physical, radio, and implementation-level attacks** (§2.4).
6. **Credential coercion**, and **the case where the abuser is the owner** — the monitor faithfully enforces the owner's authority, including an abusive owner's.
7. **Overhead under physical-radio latency** — we measure virtual devices only (§7-C9).
8. Nothing about **data already exfiltrated** before the transition. Revocation is not retro-active on copies.

### 5.10 Algorithm 9 — `TTE` (time-to-extinction estimator)

```
A9  TTE(p, d, c, g, H, π) -> epochs ∪ {∞}
 1  H' ← state at g.t_end                            # the moment the grant should die
 2  last ← ⊥
 3  for t = g.t_end to τ_max:
 4      if ∃ τ ∈ REACH(H'@t, 𝒜_p, β, 1) with EFFECT(p,d,c) : last ← t
 5      H' ← tick(H')
 6  if last = τ_max: return ∞                        # never observed to extinguish within budget
 7  return (last − g.t_end)
```

Line 6 returns `∞` conservatively and the paper must report it as "unbounded **within budget** `τ_max`", never as "unbounded" — that distinction is `UNRESOLVED-BUDGET` vs `FALSIFIED` from §1.7.

---

## 6. Methods by thrust

**Thrust α — calculus and determinacy (FLOOR).** Build CALC (§1) and INST(π) for all four platforms. Run **A6** over the full `platform × transition × property` grid to produce SPEC and CONT with contingency certificates. Run **A1–A3** at exhaustive scope to obtain RRC per cell. Deliverables: the calculus, the mechanization, executability lemmas, the determinacy table, the contingency theorem. *Stands regardless of the gate.*

**Thrust β — composed residual authority (CEILING, under test).** For every cell with `RRC > 0`, run **A4** for CRD, then **A5** for necessity with matched budget. Publish CRA only where A5 returns PASS. Run **A7** beyond exhaustive scope with statistics per §11.4. Deliverable: the CRA taxonomy with necessity-tested traces — or, if A4 returns only `CRD = 1`, an honest negative that spine (B) is false and the gate fires EXIT-B/C.

**Thrust γ — enforcement (DEPENDENT; do not start before the gate).** Implement **A8** at the HA integration boundary in Docker with virtual devices (`demo`, `template`, MQTT). Measure MO. Develop safe-exit templates. *What A8 must enforce is determined by the gate exit,* which is precisely why §13 says build nothing here until Stage 3 resolves.

---

## 7. Challenges and mitigations

**C1 — Documentation is a moving target.** Help articles change silently; a cited semantics may not exist at review time. *Mitigation:* every source snapshotted with SHA-256 and retrieval timestamp into the capability record, mirrored to archive.org, and **re-verified in the two weeks before submission** with a diff report shipped in the artifact. A changed doc becomes a finding about platform volatility, not a broken citation.

**C2 — Documented ≠ implemented.** The central validity threat. *Mitigation:* the claim is scoped to documented semantics **in the title-adjacent framing, the abstract, and every results table header** — not just in a limitations paragraph (decision D2). Plus the Stage 7 Home Assistant confirmation arm, where L2 ≈ L3, giving one platform where documented and implemented can actually be compared. Physical-device confirmation is named as future work with a cost estimate, not claimed.

**C3 — Vacuous proofs.** The standard failure of mechanized security models: a model that admits no legitimate workflow proves every property trivially. *Mitigation:* executability lemmas for **every** legitimate workflow (onboard a partner, grant a timed guest, evict a roommate, transfer a home, revoke a delegation) are a **hard Stage 0 gate**. No property result is recorded, let alone trusted, until all executability lemmas pass. A property "proved" over a vacuous model is classified VACUOUS, not HOLDS.

**C4 — Small-scope incompleteness.** Alloy at `k_P ≤ 6` may miss a deeper counterexample. *Mitigation:* (a) the I5 argument that documented harms are small; (b) scope escalation until timeout with the **reached scope reported in every table cell**, so no reader mistakes "no counterexample at scope 6" for "no counterexample"; (c) the Tamarin unbounded arm for DNA, which is the one property where depth genuinely matters.

**C5 — Coder subjectivity in DETERMINED/CONTINGENT/SILENT.** The determinacy instrument is only as good as the coding. *Mitigation:* two independent coders per cell, **Cohen's κ ≥ 0.70 required** before any SPEC value is used; all disagreements adjudicated by a third pass and the adjudication log shipped. If κ < 0.70 the codebook is revised and coding restarts — this is a real possibility and is budgeted for.

**C6 — Dual-model combinatorial explosion.** `n` silent cells naively give `2ⁿ` global models. *Mitigation:* readings enumerated **per transition**, not globally (A6 line 4); exactly two readings per silent transition; and only cells where the property actually flips enter `CONT`. Cross-transition interaction is examined only for the flagship scenario, where it is enumerated explicitly.

**C7 — Dual-encoding drift.** Alloy and Tamarin models of "the same" system can diverge and silently verify different things. *Mitigation:* a shared set of **cross-encoding conformance tests** — the same 20 concrete configurations run through both encodings with `A2` as reference semantics, requiring identical verdicts — is a Stage 0 exit condition alongside the executability lemmas.

**C8 — Boundary erosion with FABRICPROOF.** Reusing the substrate invites re-proving Matter properties and duplicating the sibling's contribution. *Mitigation:* D3's boundary is enforced mechanically — TENANTSAFE's property set contains no statement about fabrics or operational certificates; FABRICPROOF results are *imported as assumptions*, cited, never re-derived.

**C9 — No hardware.** *Cost, stated plainly:* MO is measured against virtual devices, so it excludes physical radio latency and vendor cloud round-trip. The honest framing is that MO is the **monitor's own added cost in isolation**, which is the quantity a reader actually wants (radio latency is identical with and without the monitor and would only dilute the comparison), but the absence of an end-to-end number is a limitation and is reported as one.

**C10 — Reviewer confusion with the authentication literature.** *Mitigation:* the identification-vs-authority disambiguation is a titled paragraph in §2 of the paper, not a related-work sentence, and the four properties are stated in terms a reader cannot mistake for key-establishment goals.

**C11 — Publication harm (ethics, decision D4).** The same analysis that shows how to eliminate residual access shows how to retain it covertly. *Mitigation:* attack traces are published as **model-level formal traces**, not operational procedures; no step-by-step covert-retention guidance; coordinated disclosure to affected vendors precedes publication, with an M2 checkpoint trigger that moves disclosure *ahead* of publication if a falsification implies large-scale current exposure. Safe-exit templates are developed with IPV advocacy input; **if no advocacy partner is secured, the templates ship as research artifacts explicitly not validated as user-facing guidance** — the fallback is stated now so it cannot be rationalized later.

---

## 8. Contributions

| | Contribution | Gate-dependent? |
|---|---|---|
| **C-A** | The **transition calculus** for household authority, with the authority residue (Def. 1) as its central object and revocation-completeness as residue-emptiness (Def. 2) — a statement instant-based models cannot express. | **No — stands regardless.** |
| **C-B** | **Mechanization** with structurally justified dual encoding (Alloy for bounded falsification, Tamarin for unbounded invariants, TLC for timed), passing executability lemmas and cross-encoding conformance. | **No — stands regardless.** |
| **C-C** | The **specification-determinacy instrument** (Defs. 5–6) and the per-platform per-transition determinacy table with contingency certificates — silence rendered as a theorem, not a survey. | **No — stands regardless.** |
| **C-D** | **Composed Residual Authority** (Def. 4): named, necessity-tested, matched-budget-controlled, with traces. | **Yes — EXIT-A only.** |
| **C-E** | **TSMON**, a reference monitor enforcing the verified calculus at the HA integration boundary, with measured overhead and an explicit non-guarantee list. | Artifact stands; *content* set by the exit. |
| **C-F** | **IPV-informed safe-exit templates**, with the honest fallback of §7-C11 if advocacy input is not secured. | Stands, conditionally. |

C-A, C-B and C-C are the floor. They are three contributions, all formal, and they are what makes an EXIT-B or EXIT-C paper still an IEEE S&P paper rather than a workshop note.

---

## 9. Predeclared catalog

**Declared before Stage 3 runs. Fixed. This is the mechanism that prevents "damage" from being defined after the fact.**

### 9.1 The four properties

| ID | Property | Formal statement | Prior expectation (on record, `jrn_01M0EEFTD3JZVY97Z3V9PZMM44`) |
|---|---|---|---|
| **RC** | Revocation-completeness | `∀p,H. Res(p, evict, H) = ∅` | likely FAILS or CONTINGENT |
| **NRT** | No-residual-access-after-transfer (**bidirectional**) | `Res(prior_owner, transfer, H) = ∅` **∧** `∀(d,c) ∈ prior-owner-state. ¬Effect(new_owner,d,c)` | likely FAILS or CONTINGENT |
| **DNA** | Delegation-non-amplification | `∀ g' derived from g. scope(g') ⊆ scope(g) ∧ window(g') ⊆ window(g) ∧ g'.δ < g.δ` | likely **HOLDS** on most platforms |
| **GTB** | Guest-time-bounding | `∀ g with t_end < ∞. TTE(g) = 0` | likely FAILS or CONTINGENT |

Recording the prior expectation is deliberate. If DNA turns out to fail, that is a *more* interesting result and we must be able to show we did not expect it.

### 9.2 Severity classes (of a residue)

| Class | Meaning |
|---|---|
| **S0** NONE | `Res = ∅` under all readings. |
| **S1** OBSERVATIONAL | read of non-sensitive state (is a light on). |
| **S2** SENSITIVE-READ | read of location, presence, history, or recordings. |
| **S3** ACTUATION | control of a device with physical effect (lights, thermostat, speaker). |
| **S4** SAFETY-CRITICAL | control of locks, garage, cameras (incl. disabling), alarms. |
| **S5** AUTHORITY-REGENERATIVE | the removed principal can restore their own or another's authority — the fixpoint case, strictly worse than S4 because it is self-healing against remediation. |

### 9.3 Persistence classes

| Class | Meaning |
|---|---|
| **P0** | extinguishes at next credential refresh, no action needed. |
| **P1** | extinguishes at a documented, bounded time. |
| **P2** | extinguishes only on an action the remaining household **must know to take**. |
| **P3** | not extinguished by any documented action short of factory reset. |
| **P4** | survives factory reset. |

P2 is singled out because it is the class where the *documentation* is the safety control — and where §1.6's silence measurement bites hardest.

### 9.4 Predeclared success thresholds

- **Stage 0 exit:** 100% of executability lemmas pass **and** 20/20 cross-encoding conformance tests agree. No exceptions, no partial credit.
- **Stage 1 exit:** Cohen's κ ≥ 0.70 on determinacy coding.
- **Gate / EXIT-A:** ≥ 1 cell with `RRC > 0`, severity ≥ **S3**, `CRD ≥ 2`, `A5 = PASS`, on ≥ 1 shipping platform, under a **DETERMINED** reading.
- **Gate / EXIT-B:** no EXIT-A cell, **and** `Σ_π CONT(π) ≥ 8` across the 4×6×4 grid (≥ ~8% of cells contingent).
- **Gate / EXIT-C:** neither.
- **Thrust γ acceptance:** TSMON closes 100% of the residues identified at the gate for HA-mediated paths, with **median MO ≤ 5 ms and p99 ≤ 25 ms** per authorization decision.

---

## 10. Scenarios

### SC-1 — FLAGSHIP: the deputy automation across eviction

| | |
|---|---|
| **Mechanism path** | `A1` lines 7–10 (deputy automation) ∘ surviving trigger entity ∘ absence of cascade-on-removal |
| **Steps (CRD)** | 3 |
| **Property violated** | **RC** (revocation-completeness) |
| **Severity / persistence** | **S4** (door lock) / **P2** |
| **Capability required** | `retains_authored_automations: true`, `retains_trigger_entity: true`, `retains_local_network: false`, `retains_live_session_token: false`, `β = 20` |

**Setup.** Partner `p` is a household member. `p` authors automation `a = ⟨author: p, trigger: presence(phone_p), effect: (front_door, unlock)⟩` — an ordinary convenience rule. The automation executes with *household* authority. `p`'s phone is registered as a device tracker entity `phone_p`, created as a household entity. Owner `o` evicts `p`: member list updated, every grant row naming `p` deleted. The ACL is clean by inspection.

```
CLEAN trace (what the platform's own model predicts)
  t0  evict(p)
  t1  AUTH(p, front_door, unlock, H') = FALSE          # policy denies
  t2  p attempts direct unlock                          -> DENIED
  t3  Res(p, evict, H) = ∅                              # RC holds
      VERDICT: HOLDS

ATTACK trace (what A1-A3 finds)
  t0  evict(p)
      surviving objects: a = ⟨author:p, trigger:presence(phone_p), effect:(front_door,unlock)⟩
                         phone_p  (device_tracker entity, household-owned, NOT deleted)
                         cascade-on-removal: ABSENT
  t1  AUTH(p, front_door, unlock, H') = FALSE           # policy still denies. ACL clean.
  t2  p moves into geofence of phone_p
  t3  trigger presence(phone_p) fires
  t4  A1 line 8:  a.effect = (front_door, unlock)        MATCH
      A1 line 9:  TRIGGERABLE_BY(presence(phone_p), p)   TRUE
      A1 line 10: AUTHORIZED(a.author_authority, ...)    TRUE  <-- checked against the AUTOMATION,
                                                                    never against p
  t5  EFFECT(p, front_door, unlock) = TRUE
      Res(p, evict, H) = {(front_door, unlock)}          # RC FALSIFIED
      RRC = 1, severity = S4, persistence = P2

  MINDEPTH (A4):  W = { a, phone_p, ¬cascade } , |W| = 3  -> CRD = 3
  Def.4 clause (v): no surviving object names p as SUBJECT.
                    (a names p as AUTHOR, which is not the authorization path.)  SATISFIED
```

**Why no simpler version reaches it.** A depth-1 residue would require some surviving object to name `p` as an authorized subject — precisely what eviction deletes and what any audit UI would surface. Here `p` appears only as an *author*, a field no authorization check consults. That is why row-deletion (baseline B1) cannot close it: B1 inspects subjects.

**Necessity (A5).** Remove `a` → no effect path, residue collapses. Remove `phone_p` → trigger never fires, residue collapses. Add cascade-on-removal → automation disabled at eviction, residue collapses. All three load-bearing ⇒ `CRD = 3` confirmed. Matched-budget control: no single surviving object reaches `(front_door, unlock)` within `β = 20`. **A5 = PASS.**

### SC-2 — Orphaned sub-delegation

| | |
|---|---|
| **Mechanism path** | delegation chain survives issuer removal |
| **Steps (CRD)** | 2 |
| **Property** | **RC**, and **DNA** if the orphan widens |
| **Severity / persistence** | S3 / P3 |
| **Capability** | `role_before: partner` with `manage_members`; `β = 10` |

Owner grants partner `p` `manage_members`. `p` grants guest `q` actuation on the living-room devices. Owner evicts `p`. **Does `q`'s grant survive?** Documentation on all three cloud platforms is expected SILENT here. If it survives and `p` controls `q` (a second account `p` created), residue. `W = { grant(p→q), absence-of-cascade }`, `CRD = 2`.

```
ATTACK trace
  t0  grant(o -> p, manage_members)
  t1  grant(p -> q, (living_room, actuate), delta=0)
  t2  evict(p)                      # grants WHERE subject=p deleted; grants WHERE issuer=p: ???
  t3  reading_A (cascade):    grant(p->q) revoked  -> Res = ∅          RC holds
      reading_B (no cascade): grant(p->q) survives -> Res = {(living_room,actuate)} via q
  t4  v_A ≠ v_B  ->  SPEC = CONTINGENT ; CONT += 1 ; emit CONTINGENCY_CERT
```

This is the archetypal **CONTINGENT** cell and the likeliest single source of `CONT` mass.

### SC-3 — Transfer, both directions

| | |
|---|---|
| **Mechanism path** | (A) prior-owner cloud link survives; (B) history readable by new owner |
| **Steps (CRD)** | 2 (A) / 1 (B) |
| **Property** | **NRT**, both conjuncts |
| **Severity / persistence** | S4 / P3 (A); S2 / P4 (B) |

Direction A is the resale harm: prior owner retains an ecosystem binding, `Res(prior_owner, transfer, H) ≠ ∅`. Direction B is its mirror and matters just as much for consumer harm: the new owner reads the prior owner's recordings, presence history, and routines. B is deliberately `CRD = 1` — it is not CRA, it is a plain data-residue defect, and classifying it honestly as such is part of the discipline.

### SC-4 — Guest window versus token lifetime

| | |
|---|---|
| **Mechanism path** | `A1` lines 4–6 (live-session path) |
| **Steps (CRD)** | 1, or 2 if the token auto-refreshes |
| **Property** | **GTB** |
| **Severity / persistence** | S3 / P0 or P3 |

Guest granted 4 epochs. Token minted with 24-epoch lifetime. `A9` returns `TTE = 20`. If the token auto-refreshes while any session is live, `TTE = ∞` within budget and `W = { token, refresh-policy }`, `CRD = 2`.

### SC-5 — Multi-ecosystem binding

| | |
|---|---|
| **Mechanism path** | `A1` lines 11–13 (secondary ecosystem) |
| **Steps (CRD)** | 2 |
| **Property** | **RC** |
| **Severity / persistence** | S3–S4 / P3 |

Device bound to both Google Home and Alexa. Removal from one ecosystem leaves the other's grant store untouched — neither platform documents cross-ecosystem cascade, and structurally neither can. `W = { binding(π'), absence-of-cross-ecosystem-cascade }`. **This is where FABRICPROOF composes**: its multi-admin Matter ACL model supplies the protocol-layer fact that a device legitimately holds two admins, which TENANTSAFE consumes as an assumption and never re-derives (C8).

### 10.6 Scenario-to-instrument summary

| Scenario | Property | Metrics instrumented | Algorithms | Expected class | CRA? |
|---|---|---|---|---|---|
| **SC-1** deputy automation | RC | RRC, CRD, SPEC | A1, A3, A4, A5 | S4 / P2 | **Yes, depth 3 — flagship** |
| **SC-2** orphaned sub-delegation | RC, DNA | RRC, CRD, SPEC, CONT | A1, A3, A4, A6 | S3 / P3 | Yes, depth 2 |
| **SC-3A** transfer, prior owner | NRT | RRC, CRD, SPEC | A1, A3, A4 | S4 / P3 | Yes, depth 2 |
| **SC-3B** transfer, new owner reads | NRT | RRC, SPEC | A1, A3 | S2 / P4 | No — depth 1, defect class |
| **SC-4** guest token | GTB | TTE, RRC, CRD | A1, A3, A9 | S3 / P0–P3 | Conditional |
| **SC-5** multi-ecosystem | RC | RRC, CRD, SPEC | A1, A3, A4 | S3–S4 / P3 | Yes, depth 2 |

Every metric in §1.7 is instrumented by at least one scenario; every scenario is mapped to metrics. MO is instrumented by Stage 6 rather than by a scenario, since it measures the defense and not the phenomenon.

---

## 11. Evaluation design

### 11.1 Staged pathway

| Stage | Content | Exit condition | Gate? |
|---|---|---|---|
| **0 — Substrate** | Port FABRICPROOF Tamarin ACL model; build Alloy base + TLC timed module; encode `A1`; write executability lemmas for all five legitimate workflows; run 20 cross-encoding conformance tests. | **100% executability lemmas pass AND 20/20 conformance.** Hard stop otherwise (C3, C7). | — |
| **1 — Harvest + coding** | Build the documentation corpus for all four platforms at L0/L1 (L2 for HA). Two independent coders assign SPEC per `(π, e, φ)` cell. Snapshot + hash everything. | **κ ≥ 0.70**; else revise codebook and recode. | — |
| **2 — Instantiation** | INST(π) for four platforms; dual readings via `A6` for every SILENT transition; capability record emitted per cell. | All 4×6 transitions instantiated or explicitly marked N/A. | — |
| **3 — THE GATE** | Exhaustive falsification: `A2/A3` over `4 platforms × 6 transitions × 4 properties × ≤2 readings`, at `k_P ≤ 6, k_D ≤ 4, δ_max ≤ 3`. Then `A4` (CRD) and `A5` (necessity) on every `RRC > 0` cell. | **One of EXIT-A / EXIT-B / EXIT-C fires (§13).** | **YES** |
| **4 — Unbounded** | Tamarin inductive proofs for DNA; scope escalation for RC/NRT until timeout, reached scope recorded per cell. | Verdict or documented `UNRESOLVED-BUDGET` with scope. | — |
| **5 — Scale** | `A7` sampled search beyond exhaustive scope, `N = 1000` per platform, stratified generator, seeds recorded. | Sampled statistics per §11.4. | — |
| **6 — Monitor** | `A8` at the HA integration boundary, Docker, virtual devices only. Closes gate-identified residues; measure MO. | 100% HA-mediated residue closure; median MO ≤ 5 ms, p99 ≤ 25 ms. | — |
| **7 — HA confirmation arm** | The one place L2 → L3 is possible: run the modeled transitions against a live self-hosted HA and compare documented-vs-implemented. | Agreement report; any divergence is a first-class finding. | — |

Stages 0–3 are the critical path. **Stage 6 does not begin until Stage 3 resolves.**

### 11.2 Baselines

| ID | Baseline | Role |
|---|---|---|
| **B0** | No access control. | Sanity floor. Trivial. |
| **B1** | **ACL-row deletion** — on eviction, delete every grant whose *subject* is `p`. | **THE MANDATORY HARDEST BASELINE.** This is what a competent engineer implements and what platforms document themselves as doing. The entire ceiling claim is that residue survives B1. **If B1 closes every residue, spine (B) is false and there is no EXIT-A.** |
| **B2** | KRATOS-style instant policy with conflict negotiation, extended naively across `evict`. | Shows the incumbent design point does not transfer to transitions — the positioning claim, made concrete rather than asserted. |
| **B3** | Matter fabric removal alone (FABRICPROOF protocol-layer revocation). | Shows protocol-layer revocation does not imply human-authority revocation — the D3 boundary, demonstrated. |

B1 is the one that decides the paper. It is stated here in the strongest form we can give it precisely so that beating it means something.

### 11.3 Metrics

RRC, CRD, SPEC, CONT, TTE, MO — all defined in §1.7 before use. Reported per `(platform, transition, property, reading)` cell, each with its capability record and, at Stage 4, its reached scope.

### 11.4 Statistics

**Exact arms need no inference, and we say so.** Stages 3 and 4 are exhaustive within scope: a counterexample either exists in the bounded space or does not. Reporting a p-value on an exhaustive enumeration would be a category error. These results are reported as verdicts with scopes, never as estimates.

**Sampled arms need inference, and get it.**
- **Stage 5 (`A7`).** `N = 1000` households per platform, stratified by role mix and delegation depth. Outcome `RRC > 0` modeled with a **mixed-effects logistic regression**: fixed effects for platform, transition type, and household size; **random intercepts for scenario template and for generator stratum**. Report odds ratios with 95% profile-likelihood CIs. Held-out split: generator seeds partitioned 70/30, model fit on the first, predictive check on the second.
- **Stage 6 (MO).** Paired design — identical operation sequence with and without TSMON. **Paired Wilcoxon signed-rank** on per-operation latency, plus a **mixed-effects model with random intercept for operation type**. Report median, IQR, p99, and bootstrap 95% CIs. **Never a bare point estimate** — every latency number carries an interval.
- **Stage 1 (coding).** Cohen's κ with 95% CI; per-cell agreement matrix shipped.

**Preregistered contrast set — exactly five, fixed before Stage 3:**
1. `RRC > 0` rate under **B1** vs under TSMON *(does the obvious fix suffice? — the ceiling test)*
2. `CRD ≥ 2` proportion among residues *(is residue composed? — spine (B))*
3. `CONT` across the four platforms *(does silence differ by platform?)*
4. `TTE` for guest grants, documented bound vs measured *(GTB)*
5. MO with vs without TSMON *(cost of the defense)*

No other contrast is reported as confirmatory. Anything else that turns up is labelled exploratory in the paper text.

### 11.5 Key ablations

- **A-1 Necessity ablation** (`A5` lines 2–5): remove each witness object in turn; residue must collapse. Without this, CRD is a claim rather than a measurement.
- **A-2 Matched-budget ablation** (`A5` lines 7–9): single-object adversary at identical `β`. Excludes "the composed version merely spent more."
- **A-3 Reading ablation**: every CONTINGENT cell re-run under both readings, both reported. Never collapse to one.
- **A-4 Cascade ablation**: add cascade-on-removal to each platform model; measure how much residue it eliminates. This is the **actionable recommendation to vendors** and quantifies it rather than asserting it.
- **A-5 Provenance ablation**: disable `A8` lines 5–10 (provenance tracking), keep only line 1. Reduces TSMON to B1 and should restore the residue — the direct counterfactual that provenance tracking is what does the work.

---

## 12. Detailed paper outline

Written for the strongest ceiling (EXIT-A). §13 names which section re-centers under each exit.

| § | Section | Thrust | Driving question | Primary figure/table |
|---|---|---|---|---|
| 1 | Introduction | — | Why are the harms all transitions when the models are all instants? | Fig. 1 — timeline of a separation with the residue highlighted |
| 2 | Background: **identification vs authority** | — | Why does existing formal smart-home work not answer this? | Table 1 — prior work × {instant/transition} × {identification/authority} |
| 3 | Threat model: the interpersonal adversary | — | Who is the adversary and what do they actually retain? | Table 2 — capability record schema, instantiated |
| 4 | A calculus of household transitions | α | What is the formal object? | Fig. 2 — configuration and transition semantics; **Def. 1 (residue)** |
| 5 | Mechanization and tool choice | α | Why these tools, and is the model faithful? | Table 3 — property structure → tool; executability + conformance results |
| 6 | **Results: residue across platforms** | α, β | What holds, what fails, what is undecidable-by-documentation? | **Table 4 — the 4×6×4 verdict grid** (RRC, CRD, SPEC, severity, scope) |
| 7 | Composed residual authority | β | Is residue composed, and does the obvious fix miss it? | Fig. 3 — SC-1 witness decomposition; necessity + matched-budget results |
| 8 | Under-specification as a finding | α | How much safety hinges on undocumented choices? | Fig. 4 — `CONT` per platform with contingency certificates |
| 9 | TSMON: enforcing the calculus | γ | Can it be closed, and what does it cost? | Fig. 5 — MO distribution, paired, with CIs; closure table |
| 10 | Safe exit, and what we cannot fix | γ | What does this actually do for a person leaving? | Table 5 — non-guarantees, incl. abuser-as-owner |
| 11 | Limitations and ethics | — | What is the validity of a documented-semantics claim? | — |
| 12 | Related work | — | Positioning against both adjacent literatures | — |

§6 is the paper's center of gravity and the section that moves under a different exit.

---

## 13. The arc and the gate

### The acts

- **Act I (Thrust α) — THE FLOOR.** The transition calculus, its mechanization, and the determinacy instrument. Delivers C-A, C-B, C-C. Stands whether or not any platform is shown to be violating anything, because the contingency certificates are formal artifacts, not opinions. **Act I is the paper's floor.**
- **Act II (Thrust β) — THE CEILING.** Composed Residual Authority: that residue is compositional and therefore survives the fix platforms actually implement. Under test.
- **Thrust γ — enforcement**, dependent on the exit.

### The gate: Stage 3

**Build nothing below this until it resolves.** Concretely: do not implement TSMON, do not write §9 or §10 of the paper, do not begin M3.

Current data leans toward **EXIT-B**. The project's own pre-registered expectation (`jrn_01M0EEFTD3JZVY97Z3V9PZMM44`) is that under-specification dominates and that DNA holds while the other three fail or are contingent. That lean is exactly why the gate is placed early: at IEEE S&P, EXIT-B is a materially harder sell than EXIT-A, and we need to know which paper we are writing before six weeks of monitor engineering are spent.

| Exit | Condition | Paper that gets written | Section that re-centers | Claim ceiling |
|---|---|---|---|---|
| **EXIT-A** *falsify* | ≥1 cell: `RRC>0`, severity ≥ **S3**, `CRD≥2`, `A5=PASS`, under a **DETERMINED** reading, on a shipping platform | **"Composed Residual Authority in Smart-Home Households"** — C-A…C-E | **§6 and §7** become the core; §7 leads with the necessity-tested witness decomposition | Platforms are **wrong**, mechanically demonstrated, and the fix they implement is insufficient by construction. Strongest paper. |
| **EXIT-B** *contingent* | no EXIT-A cell, but `Σ_π CONT(π) ≥ 8` | **"Authority Across Household Transitions Is Under-Specified"** — C-A, C-B, C-C, C-E, C-F | **§8 becomes the core**; §6 demotes to supporting; §7 reports the honest negative that residues found were depth-1 | We cannot say platforms are wrong — **and neither can a user**, which we prove. TSMON reframes as a *prophylactic* that is correct under both readings. Publishable; needs §8 to be exceptionally well executed. |
| **EXIT-C** *holds* | neither | **"A Calculus for Household Authority Transitions"** — C-A, C-B, plus a negative result | **§6 becomes a verification report**; §7 is cut; §5 (mechanization) is promoted to the technical core | A reusable calculus and an honest negative. Weakest. **Raise a PI checkpoint immediately** — this likely re-targets to CAV/FM/CSF rather than S&P, and that is a decision above the Executor. |

### Floor / ceiling / which paper

- **Floor:** a transition calculus with a mechanized, executability-checked model and a formal instrument that turns documentation silence into a certified quantity. Three contributions, all formal, independent of what the platforms turn out to do.
- **Ceiling:** that residual authority is *composed* — assembled from surviving objects none of which names the removed principal — which explains why ACL-row deletion cannot close it, demonstrated with necessity-tested traces and closed by a measured reference monitor.
- **Which paper:** decided at Stage 3, by whether a severity-≥S3 residue with `CRD ≥ 2` exists under a DETERMINED reading on a shipping platform.

### Validity claim — stated once, and not permitted to drift

**All results concern DOCUMENTED semantics, not implemented behavior**, for Google Home, Alexa and SmartThings. Home Assistant is the single exception, where open source and a runnable instance put L2 ≈ L3 and a genuine documented-vs-implemented comparison is possible at zero hardware cost (Stage 7). Physical-device confirmation is **named future work with a cost estimate, not a claim** — decision D2 as amended for the no-hardware constraint. Every results table carries the validity scope in its header, not in a footnote.
