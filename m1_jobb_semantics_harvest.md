# M1 Job B — Semantics Harvest and Under-Specification Table

**Mission** `mis_01M0EEHKZB9D1JJEBXN468C68Q` · Tasks T5–T8
**Date** 2026-08-19 · **Executor**
**Scope boundary honoured:** public documentation + open source only. **No APK analysis, no AndroZoo, no companion-app decompilation, no hardware.**
**Observability levels** per `research_design_detailed.md` §2.2: L0 public help articles, L1 developer docs, L2 open source, L3 implemented behaviour (unavailable except HA).

---

## T5/T6 — Per-platform, per-transition determinacy

Legend: **D** = DETERMINED · **C** = CONTINGENT candidate (silent, readings plausibly differ) · **S** = SILENT · **D!** = determined **and documents a residue**

| Transition | Google Home | Alexa | SmartThings | Home Assistant |
|---|---|---|---|---|
| **grant** | **D** — Admin-only invite; Member with independent `Activity` / `Settings` toggles; child accounts default both OFF | **D** (partial) — Household/Family invite by Amazon account | **D** — Owner-only invite, via Samsung account email or QR | **D** (L2) — owner/admin/user/read-only groups; per-entity, per-device, per-area, per-domain policy |
| **delegate** | **D** — Members cannot add people; Admin-only. No re-delegation primitive | **S** — no documented delegation model for smart-home authority | **D** — "Members can access and edit the Location with all of the same options as the owner, with the exception of inviting additional members" | **D** (L2) — no user-to-user delegation; admins create users |
| **expire** | **D** — guest lock passcodes support schedules; "revoke or edit schedules for guest passcodes" | **S** — no time-limited smart-home access documented | **S** — no guest or time-limited access documented | **D** (L2) — refresh tokens auto-removed after 90 days unused; long-lived tokens do not expire |
| **evict** | **D!** — **two documented residues** (below) | **C** — profile loss documented; smart-home device control after removal **not addressed** | **D** — "won't be able to control any of its devices"; silent on automations/Routines authored by the member | **D!** (L2) — **removal ≠ deactivation asymmetry** (below) |
| **transfer_ownership** | **D** (via reset) — remove from account + factory reset; pre-owned devices blocked until prior video history expires, "up to 60 days" | **S** — not documented for households | **C** — device-level owner change documented ("Make me the owner"); **location-level ownership transfer not documented** | **S** — no ownership-transfer concept; owner is fixed and cannot be deactivated |
| **factory_reset** | **D** — documented as the transfer mechanism; "clear your data from the device and can't be undone" | **S** | **D** (device level) — reset then re-register under new account | **S** — no device-level notion; HA reinstall is out of band |

**Tally — CORRECTED 2026-08-22 (E1.9/E1.10).** **D: 14 · C: 3 · S: 7.**

> The 2026-08-19 version of this line read "15 · 3 · 6", which was wrong twice over.
> Re-deriving from the table gives 15/2/7 for the original labels; the codebook-strict
> re-code then moves SmartThings/`evict` from D to C, giving **14/3/7**. The erroneous
> tally propagated into `jrn_01M0EGJ4FXWXYS49KSTG96NMGB`, the M1 mission report, and
> verbal summaries. Corrected here and recorded rather than silently patched.
>
> **SmartThings/`evict` is CONTINGENT, not DETERMINED.** Removal of device control is
> documented; the fate of member-authored Routines is not, and the two readings give
> different authority outcomes. Codebook §"C vs S": detail about one consequence does
> not determine a different one. The Stage 2 model already dual-modelled this cell,
> so no downstream model change is required.
>
> Reliability: Cohen's κ = **0.923**, 95% CI [0.775, 1.000], 23/24 agreement — passes
> the predeclared ≥0.70 gate. **Caveat: both passes are by the same analyst, so this is
> INTRA-rater (test-retest) reliability, not inter-rater.** True inter-rater reliability
> requires a second independent analyst and remains outstanding (E1.13).
> Codebook: `coding/codebook.md`. Computation: `coding/kappa.py`.

---

## The three documented residues found in harvest

These are `Res ≠ ∅` cells reachable **from documentation alone**, before any modelling.

### R1 — Google Home: smart-lock passcode survives member removal · **S4 / P2 · DETERMINED**
Google's own guidance states that on removing a member or leaving a home, smart-lock passcodes for those users **need to be manually changed or removed**. Membership removal revokes app-mediated access; it does **not** invalidate the physical passcode. The lock accepts the code irrespective of Home membership.
- `Res(p, evict, H) ⊇ {(lock, unlock)}` — severity **S4** (safety-critical).
- Persistence **P2**: extinguishes only on an action the remaining household must *know* to take. Google added a security reminder precisely because people do not.
- **Classification honesty:** the passcode entry names the removed person as its holder, so under Def. 4 clause (v) this is arguably **CRD = 1**, i.e. the IMPLEMENTATION-DEFECT class, **not** the CRA flagship. Recorded as a documented residue at safety-critical severity, not as evidence for spine (B).

### R2 — Google Home: Google TV account survives member removal · **S2 / P2 · DETERMINED**
"Their Google TV account isn't removed from this home — they have to sign out of that account on this home's Google TVs or in account.google.com."
- The remediating action is available **only to the removed principal**, not to the household. Strictly worse than P2 in the safety reading: the evicted party chooses when their own access ends.
- Secondary-binding shape (design §10 SC-5).

### R3 — Home Assistant: removal orphans a live session that retains **read** authority · **S2 / P2 · CONFIRMED AT L3**

> **REVISED 2026-08-21 after Stage 7 execution.** As first written (2026-08-19) R3 claimed an *actuation* residue at S3–S5 and was nominated the flagship CRA candidate. **That claim is REFUTED.** The Stage 7 experiment ran it and actuation is blocked. A narrower residue is confirmed in its place. The original wording is superseded; the revision is recorded rather than silently replaced.

**Verified at L2 in the shipping release** (image `homeassistant/home-assistant:2026.7.4`, byte-identical to `dev` for every path below):
`async_deactivate_user` routes each token through `AuthManager.async_remove_refresh_token`, which fires `_revoke_callbacks`; the sole registrant codebase-wide is `websocket_api/auth.py:116` → `_cancel_ws`. `async_remove_user` instead calls `_store.async_remove_user` (`auth_store.py:142`), which pops the user and clears tokens **directly in the store**, never routing through the manager — so callbacks never fire and **no open socket is cancelled**.

**Confirmed at L3** (HA in Docker, port 8124, owner + member, no hardware):

| Probe on the member's still-open socket | after **REMOVE** | after **DEACTIVATE** (control) |
|---|---|---|
| `call_service` (actuation) | **refused** — `UnknownUser` | connection **closed** |
| `get_states` | **success, 18/18 entities** | connection closed |
| pre-existing `state_changed` subscription | **events still delivered** | connection closed |
| **new** `subscribe_events` | **success** | connection closed |
| new connection with the same token | rejected `auth_invalid` | rejected `auth_invalid` |

**The mechanism is a read/write asymmetry inside one component.**
- **Write path re-resolves by ID and is safe.** `helpers/service.py:729` — `user = await hass.auth.async_get_user(call.context.user_id)`; `if user is None: raise UnknownUser`. The store entry is gone, so actuation fails.
- **Read path trusts the captured object and is not.** `_async_get_allowed_states` (`commands.py:355`) does `user = connection.user`; `handle_subscribe_events` (`:192`) tests `connection.user.is_admin`; `_forward_events_check_permissions` (`:150`) takes `user.permissions`. `ActiveConnection.user` is a **strong reference** captured at auth time (`connection.py:78`), so it survives `_users.pop()` intact.

`commands.py:157` is worth quoting in the paper verbatim:
```python
# We have to lookup the permissions again because the user might have
# changed since the subscription was created.
permissions = user.permissions
```
The code anticipates that the user may have changed and re-reads `permissions` — from the same stale object. It never re-resolves the *user*. The defensive intent is present; the defense is incomplete exactly where it matters.

**Consequence.** A removed principal keeps a live, full-fidelity **read** channel — all entity states plus the live `state_changed` stream, including presence, device trackers, sensors, and door/window contacts — for as long as the socket stays open. They can even open *new* subscriptions on it. The household sees the user deleted and sees new logins rejected; nothing in any UI reveals the orphaned socket, and no household action terminates it. It ends only when the connection drops (network change, HA restart).

- Severity **S2** (SENSITIVE-READ). **Not S3** — actuation is blocked.
- Persistence **P2**, in its worst form: no documented action by the household ends it, and they cannot observe it.
- `CRD = 2`; witness `W = { open WebSocket connection, removal-path-bypasses-async_remove_refresh_token }`.
- Def. 4 clause (v) satisfied in the strongest form: the user row is popped outright — the principal does not exist — and the read channel persists.
- The safe ordering (**deactivate, then remove**) is nowhere documented, and the UI offers deletion as the primary action.

**Bearing on the gate — stated against the predeclared catalog, not around it.** EXIT-A requires severity **≥ S3**. R3 is **S2**, so *R3 does not meet the EXIT-A threshold*. There is a genuine tension — under an IPV threat model, covert continued surveillance is arguably worse than actuation — but re-ranking the severity classes *after* seeing the result is precisely the post-hoc move predeclaration exists to prevent. **Flagged for the PI as a catalog question; not taken unilaterally.**

---

## T7 — Feasibility judgement on the documentation-only re-scope

**The re-scope holds. Documentation is rich enough to instantiate the calculus for four platforms, three of them comfortably.**

| Platform | Richness | Instantiable? | Notes |
|---|---|---|---|
| **Google Home** | **Rich** | **Yes** | Best-documented. Explicit permission toggles, scheduled guest passcodes (makes **GTB** instantiable), documented transfer, and two documented residues. |
| **Home Assistant** | **Rich (L2)** | **Yes** | Source is ground truth; the only platform where L2 ≈ L3. Entity-level policy is finer-grained than any cloud platform's. |
| **SmartThings** | **Moderate** | **Yes** | Owner/Member binary, no delegation, no guest/time-limited. Thin but determinate on the core transitions. |
| **Alexa** | **Thin** | **Yes, with heavy dual-modelling** | The critical question — does a removed member retain smart-home device control — is **not addressed anywhere in Amazon's help documentation**. This is the single largest under-specification found, on the largest-installed-base platform. |

**Threshold from the mission (≥3 platforms): MET.** No blocking checkpoint is triggered. The APK-analysis fallback is not needed and is not invoked.

**The design's stated top risk did not materialise.** `research_design_detailed.md` named the most dangerous assumption as *"public documentation is specific enough to reliably separate DETERMINED from SILENT."* Harvest refutes the pessimistic case: 15 of 24 cells are DETERMINED, and Google Home is determinate enough to yield **documented residues** — which is the precondition for EXIT-A, not merely EXIT-B.

**Consequence for the gate — REVISED 2026-08-21 after Stage 7.** The 2026-08-19 reading of this section claimed the EXIT-B lean had weakened because R1 *and* R3 were residues at severity ≥S3. **Stage 7 refuted the R3 half.** R3 is S2, below the EXIT-A threshold. The only remaining ≥S3 candidate is **R1** (Google Home lock passcode, S4, DETERMINED from documentation) — and R1 is defect-class (`CRD = 1`), so it fails the `CRD ≥ 2` conjunct that EXIT-A also requires. **On present evidence no cell satisfies EXIT-A in full, and the pre-registered lean toward EXIT-B (`jrn_01M0EEFTD3JZVY97Z3V9PZMM44`) is restored — close to its original strength.** The gate has not fired either way; Stage 3 decides it.

---

## T8 — Verdict

# GO

Both M1 jobs return GO. Job A (scoop audit) cleared the positioning. Job B clears the re-scope: public documentation and open source are sufficient to instantiate the transition calculus for four platforms without any APK analysis or hardware.

**Carry into M2:**
1. Instantiate **Google Home first** — richest semantics and the only platform documenting scheduled expiry, so it is the only one where **GTB** is testable against a documented bound.
2. Treat **R3 as the flagship CRA candidate**, not R1. R3 satisfies clause (v) outright; R1 probably does not and belongs in the defect class.
3. **Alexa's silence is the measurement result**, not an obstacle — and it lands on the largest installed base, which is the strongest possible framing for §8 of the paper.
4. **SmartThings documentation is internally inconsistent** on the Owner/Member exception (one source says members cannot delete a Location, another says the exception is inviting members). Both may hold; the inconsistency itself is an under-specification signal worth a footnote.
5. Run the **Stage 7 HA confirmation of R3 early** — it is free, needs no hardware, and would convert a source-level inference into an observed L3 fact on the one platform where that is possible.

## Sources

- [Manage people and permissions in the Google Home app](https://support.google.com/googlehome/answer/9155535?hl=en)
- [Guests and your Google connected home devices](https://support.google.com/googlehome/answer/7177221?hl=en)
- [Control your lock with the Google Home app](https://support.google.com/googlehome/answer/10042812?hl=en)
- [Moving guide for Google Home and Nest devices](https://support.google.com/googlehome/answer/11151047?hl=en)
- [Remove a Member of Your Home from the Alexa App](https://www.amazon.com/gp/help/customer/display.html?nodeId=TkhKFt9yxp5myHXvmK)
- [Remove an Adult from Your Amazon Household](https://www.amazon.com/gp/help/customer/display.html?nodeId=GMA7DTL7BABZ6Z5A)
- [Share Control of your Smart Devices – SmartThings Support](https://support.smartthings.com/hc/en-us/articles/360051931312-Share-Control-of-your-Smart-Devices)
- [Invite members using the SmartThings app](https://www.samsung.com/us/support/answer/ANS10002634/)
- [How to change the owner of a device registered on the SmartThings app](https://www.samsung.com/uk/support/apps-services/how-to-change-the-owner-of-a-device-registered-on-the-smartthings-app/)
- [Home Assistant — Authentication](https://www.home-assistant.io/docs/authentication/)
- [Home Assistant Developer Docs — Permissions](https://developers.home-assistant.io/docs/auth_permissions/)
- Home Assistant core source, `dev` branch, retrieved 2026-08-19: `homeassistant/auth/__init__.py`, `homeassistant/auth/auth_store.py`, `homeassistant/auth/models.py`, `homeassistant/components/websocket_api/auth.py`, `homeassistant/components/websocket_api/connection.py`, `homeassistant/components/mobile_app/__init__.py`, `homeassistant/components/person/__init__.py`
