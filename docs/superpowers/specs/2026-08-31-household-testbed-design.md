# Household testbed and scenario evaluation — design

**Status:** awaiting PI review. Nothing built yet.

## Problem

The threat model asserts its own precondition. §3 says the adversary "may act
through a session established before removal", and every experiment then
*constructs* that session with a direct `websockets.connect` call. A reviewer
asks the obvious question — how does a household actually get into that state? —
and the paper has no answer beyond assertion.

A second gap compounds it. Every actuation result actuates
`input_boolean.ts_probe`, a Home Assistant helper variable. The paper says
"device actuation"; the evidence is a boolean flip.

Both are answerable without hardware, and answering them converts the weakest
part of the paper into a measurement.

## Goals

1. The precondition **arises from ordinary use** and is observed, not engineered.
2. "Device actuation" means a **real device entity** actuating through a real
   integration and a real protocol.
3. Scenarios are **grounded in the cited IPV literature**, not invented.
4. One scenario runs unchanged on **three platforms**, two local and one cloud.
5. Results land in the **Evaluation section**, not an appendix.

## Non-goals

- No hardware. No purchased devices. (Standing project constraint.)
- No Matter SDK. The build image on this host is amd64 under arm64 emulation;
  compiling the example apps costs hours with a real chance of not finishing.
  MQTT gives a real protocol stack at a fraction of the cost.
- No attempt to test transitions the platforms do not implement. Home Assistant
  and openHAB have no native ownership-transfer or guest-expiry concept; where a
  transition cannot be exercised we report that rather than simulating it.

## Architecture

Three layers — substrate, clients, scenarios — plus one shared device daemon
that serves the two local substrates. Observation is part of the scenario
runner, not a layer of its own.

### 1. Substrate adapters

A common interface with three implementations, so a scenario is written once:

```
setup()                     -> admin credential
create_member(name, role)   -> member credential
open_client(cred, kind)     -> client handle
remove_member(id)  /  deactivate_member(id)
devices()                   -> real device handles
observe(client)             -> capability vector, evaluated against real devices
```

| Adapter | Devices | Notes |
|---|---|---|
| `HomeAssistantSubstrate` | MQTT discovery | local container, already exercised |
| `OpenHABSubstrate` | MQTT | local container, already exercised |
| `SmartThingsSubstrate` | CLI virtual devices | **live cloud, PI's own account** |

### 2. Virtual device daemon

One process publishing MQTT discovery configs, consumed by each platform's real
MQTT integration. Device set chosen to span the capability lattice and to match
the harms the literature documents:

| Entity | Capability | Why this device |
|---|---|---|
| `lock.front_door` | Operate | physical-safety relevant; the actuation that matters |
| `binary_sensor.front_door_motion` | View | surveillance channel |
| `light.living_room` | Operate | presence signalling, low-severity actuation |
| `binary_sensor.presence_partner` | View | location inference |
| `climate.thermostat` | Operate | the documented "still controls the thermostat" harm |

These register as genuine entities. A lock reports `locked`/`unlocked` and
refuses malformed commands, because the platform's own lock integration is
handling it.

### 3. Client models

The piece that answers the reviewer's question. Each models a real way a
household member's device holds a connection:

| Client | How it connects | Represents |
|---|---|---|
| `browser` | Playwright drives the real HA frontend, logs in, leaves a dashboard open | laptop tab left open |
| `app` | persistent authenticated WebSocket with ping/pong | phone app backgrounded |
| `token` | long-lived access token | a script, a widget, a dashboard panel |

### 4. Scenario timelines

Declarative. `setup → ordinary use → transition → observe`, replayed per
substrate. Four scenarios, each anchored to cited work:

| Scenario | Anchor | Transition |
|---|---|---|
| Separation | Freed 2018, Matthews 2017 | member removed after ordinary use |
| Roommate move-out | Zeng 2019 | member removed, dashboard open on a laptop |
| Guest overstay | paper's own framing | time-bounded grant expires |
| Device handover | prior-owner harm | ownership/admin handover |

## Measurements

**M1 — Precondition prevalence.** For each client type, is a live authenticated
session present at the moment of removal, after ordinary use with no explicit
logout? *This is the answer to "how do you launch this."* If the precondition is
the default state of a household member's device, it stops being an assumption.

*"Ordinary use" is defined in advance so the measurement cannot be tuned to
produce the answer we want.* It is exactly: authenticate once through the
platform's own login UI; view a dashboard; issue one permitted command to one
device; then stop interacting. No page kept in the foreground, no keep-alive we
inject, no explicit logout — and no reconnection attempt by us. Whatever the
client does afterwards is the platform's and the browser's own behaviour. Any
step beyond this list is a *deviation* and must be reported as one; if we ever
need a deviation to observe a session, that is itself the finding and it weakens
rather than supports the claim.

The honest null result is worth stating up front: if ordinary use does **not**
leave a live session at removal time, then the precondition is genuinely
uncommon, §3 must be narrowed to say so, and the paper's severity claim drops.
We report that outcome if we get it.

**M2 — End-to-end capability on real devices.** After the transition, what can
the removed principal still do to `lock.front_door`, the motion sensor, the
thermostat? Reported per device and per capability class.

**M3 — Composition on a real device.** Re-confirm the CRD = 2 result with a
lock as the target: direct actuation refused, automation-induced actuation
succeeding.

**M4 — Cross-platform.** M1–M3 on all three substrates, including one
commercial cloud.

Existing results are retained as mechanism detail, not discarded.

## Ethics — changed by the SmartThings decision

Testing SmartThings makes a statement in the current Ethics Considerations
section **false**. It reads: *"No live or third-party systems... No vendor
infrastructure was contacted."* That must be rewritten before submission.

Constraints agreed with the PI:

- **Virtual devices only, on the PI's own account.** No other user's data, no
  physical device, no other household.
- **Pre-committed disclosure.** Any SmartThings finding is reported to Samsung.
  Decided *before* running, so the decision is not made under the pressure of
  holding a finding.
- The CFP's live-systems clause is answered directly: permission is ownership of
  the account; the load is a handful of API calls; nothing is disrupted.

## Page budget

The body is at 13/13. Space comes from compressing §6 (determinacy), which is
~1.5 pages reporting a negative result the paper already says is not its
principal contribution. The negative result and its table stay; the prose
around them shrinks.

## Risks

| Risk | Mitigation |
|---|---|
| Playwright cannot log into the HA frontend headlessly | fall back to the `app` client for M1; report the browser arm as not run rather than simulating it |
| SmartThings virtual devices lack a lock profile | use switch/contact profiles and report the reduced device set honestly |
| SmartThings has no removable second user on a personal account | this would make M1–M3 untestable there; report as a platform limitation, keep the read-only semantics arm |
| Testbed results contradict existing results | that is a finding, not a failure; the existing runs are on the same platforms and any divergence gets investigated and reported |

## Success criteria

- M1 produces a number for every client type on at least Home Assistant.
- M2 reports capability against at least one real lock entity.
- §3 stops asserting the precondition and cites a measurement instead.
- The Evaluation section carries scenario results with real devices.
- The ethics section accurately describes what was touched.
