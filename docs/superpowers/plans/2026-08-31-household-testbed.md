# Household Testbed Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the threat model's asserted precondition and its
`input_boolean` stand-in devices with a measured precondition and real device
entities, producing Evaluation-section results.

**Architecture:** Three layers plus a shared device daemon. Substrate adapters
present one interface over Home Assistant, openHAB and SmartThings. A daemon
publishes MQTT discovery configs that the platforms' own MQTT integrations turn
into real entities, including a door lock. Client models connect the way real
household devices do, including a headless browser driving the actual frontend.
Scenario timelines are declarative data replayed against any substrate.

**Tech Stack:** Python 3.11+, `aiohttp`, `websockets`, `paho-mqtt`,
`playwright`, `pytest`, Docker, `eclipse-mosquitto:2`, SmartThings CLI 2.1.2.

**Spec:** `docs/superpowers/specs/2026-08-31-household-testbed-design.md`

## Global Constraints

- **No hardware.** Standing project constraint. Virtual devices only.
- **SmartThings scope correction.** The public API exposes no location-members
  endpoint (404) and invitations are POST-only, so *membership revocation is not
  testable there*. SmartThings is instead used as a real cloud device substrate
  to exercise the **secondary-ecosystem binding carrier**, which the Alloy model
  includes as `Binding` and which has never been runtime-tested.
- **SmartThings account safety.** The account controls 26 devices in the PI's
  real home. Only devices we create, named with the `ts-` prefix, may ever be
  commanded. Never send a command to a pre-existing device. Never create or
  modify a Routine. Delete every `ts-` device at teardown. Capability audit shows
  18 `switch` capabilities and no lock, garage-door, valve or alarm, so the worst
  case of a mistake is a light toggling.
- **Pre-committed disclosure.** Any SmartThings finding is reported to Samsung.
- **"Ordinary use" is fixed** and may not be widened to obtain a result:
  authenticate once through the platform's own login UI; view a dashboard; issue
  one permitted command; stop interacting. No injected keep-alive, no
  reconnection by us, no explicit logout. Any deviation is reported as one.
- **Controls are mandatory.** Every probe records the pre-transition value. A
  capability the principal never held cannot be scored as residue.
- All new code lives under `testbed/`. Existing `experiments/` scripts are not
  modified; they remain valid as mechanism detail.

---

### Task 1: MQTT virtual device daemon

**Files:**
- Create: `testbed/devices.py`
- Test: `tests/test_devices.py`

**Interfaces:**
- Produces: `DeviceDaemon(host: str, port: int = 1883)` with
  `publish_discovery() -> list[str]` returning entity ids,
  `state(entity_id: str) -> str`, `set_state(entity_id: str, value: str) -> None`,
  `start() -> None`, `stop() -> None`.
- Device set: `lock.ts_front_door`, `binary_sensor.ts_front_motion`,
  `light.ts_living_room`, `binary_sensor.ts_presence_partner`,
  `climate.ts_thermostat`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_devices.py
from testbed.devices import DeviceDaemon

def test_discovery_declares_a_real_lock():
    d = DeviceDaemon("localhost")
    configs = d.discovery_payloads()
    lock = configs["homeassistant/lock/ts_front_door/config"]
    assert lock["command_topic"].endswith("ts_front_door/set")
    assert lock["payload_lock"] == "LOCK"
    assert lock["payload_unlock"] == "UNLOCK"
    assert lock["state_locked"] == "LOCKED"

def test_every_declared_entity_has_a_state_topic():
    d = DeviceDaemon("localhost")
    for topic, cfg in d.discovery_payloads().items():
        assert "state_topic" in cfg, topic
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_devices.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'testbed.devices'`

- [ ] **Step 3: Write minimal implementation**

```python
# testbed/devices.py
"""Virtual household devices published over MQTT discovery.

These are not helper variables. Each is consumed by the platform's own MQTT
integration and becomes a genuine entity of its domain: a lock reports
locked/unlocked and rejects malformed commands because the platform's lock
integration handles it, not us.
"""
import json, threading, time
import paho.mqtt.client as mqtt

PREFIX = "homeassistant"

DEVICES = {
    "lock.ts_front_door": dict(domain="lock", name="TS Front Door",
                               extra=dict(payload_lock="LOCK", payload_unlock="UNLOCK",
                                          state_locked="LOCKED", state_unlocked="UNLOCKED"),
                               initial="LOCKED"),
    "binary_sensor.ts_front_motion": dict(domain="binary_sensor", name="TS Front Motion",
                               extra=dict(device_class="motion", payload_on="ON", payload_off="OFF"),
                               initial="OFF"),
    "light.ts_living_room": dict(domain="light", name="TS Living Room",
                               extra=dict(payload_on="ON", payload_off="OFF"), initial="OFF"),
    "binary_sensor.ts_presence_partner": dict(domain="binary_sensor", name="TS Presence",
                               extra=dict(device_class="presence", payload_on="ON", payload_off="OFF"),
                               initial="OFF"),
    "climate.ts_thermostat": dict(domain="climate", name="TS Thermostat",
                               extra=dict(modes=["off", "heat"], temperature_command_topic="ts/climate/ts_thermostat/temp/set",
                                          temperature_state_topic="ts/climate/ts_thermostat/temp"),
                               initial="off"),
}

class DeviceDaemon:
    def __init__(self, host: str, port: int = 1883):
        self.host, self.port = host, port
        self._states = {k: v["initial"] for k, v in DEVICES.items()}
        self._c = None
        self._lock = threading.Lock()

    def discovery_payloads(self) -> dict:
        out = {}
        for eid, spec in DEVICES.items():
            obj = eid.split(".", 1)[1]
            base = f"ts/{spec['domain']}/{obj}"
            cfg = {"name": spec["name"], "unique_id": obj,
                   "state_topic": f"{base}/state", "command_topic": f"{base}/set"}
            cfg.update(spec["extra"])
            out[f"{PREFIX}/{spec['domain']}/{obj}/config"] = cfg
        return out

    def _on_message(self, client, userdata, msg):
        for eid, spec in DEVICES.items():
            obj = eid.split(".", 1)[1]
            if msg.topic == f"ts/{spec['domain']}/{obj}/set":
                v = msg.payload.decode()
                # a real device maps its command vocabulary to its state vocabulary
                if spec["domain"] == "lock":
                    v = {"LOCK": "LOCKED", "UNLOCK": "UNLOCKED"}.get(v)
                    if v is None:
                        return                      # malformed command: ignore, as a lock would
                with self._lock:
                    self._states[eid] = v
                client.publish(f"ts/{spec['domain']}/{obj}/state", v, retain=True)

    def start(self) -> None:
        self._c = mqtt.Client()
        self._c.on_message = self._on_message
        self._c.connect(self.host, self.port, 60)
        for topic, cfg in self.discovery_payloads().items():
            self._c.publish(topic, json.dumps(cfg), retain=True)
        for eid, spec in DEVICES.items():
            obj = eid.split(".", 1)[1]
            self._c.subscribe(f"ts/{spec['domain']}/{obj}/set")
            self._c.publish(f"ts/{spec['domain']}/{obj}/state", self._states[eid], retain=True)
        self._c.loop_start()
        time.sleep(1.0)

    def stop(self) -> None:
        if self._c:
            self._c.loop_stop(); self._c.disconnect()

    def state(self, entity_id: str) -> str:
        with self._lock:
            return self._states[entity_id]

    def set_state(self, entity_id: str, value: str) -> None:
        spec = DEVICES[entity_id]; obj = entity_id.split(".", 1)[1]
        with self._lock:
            self._states[entity_id] = value
        self._c.publish(f"ts/{spec['domain']}/{obj}/state", value, retain=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_devices.py -v`
Expected: PASS, 2 passed

- [ ] **Step 5: Commit**

```bash
git add testbed/devices.py tests/test_devices.py
git commit -m "testbed: MQTT virtual household devices including a real lock"
```

---

### Task 2: Substrate interface and Home Assistant adapter

**Files:**
- Create: `testbed/substrates/base.py`, `testbed/substrates/homeassistant.py`
- Test: `tests/test_substrate_contract.py`

**Interfaces:**
- Consumes: `testbed.devices.DeviceDaemon` from Task 1.
- Produces: `Substrate` ABC with `setup() -> str`,
  `create_member(name: str, role: str) -> dict`,
  `remove_member(uid: str) -> None`, `deactivate_member(uid: str) -> None`,
  `observe(client, devices) -> dict[str, bool]`, `teardown() -> None`.
  `HomeAssistantSubstrate(port: int, version: str)` implements it.
- Capability vector keys: `read`, `stream`, `direct_lock`, `induced_lock`,
  `user_enum`, `event_fire`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_substrate_contract.py
import inspect
from testbed.substrates.base import Substrate
from testbed.substrates.homeassistant import HomeAssistantSubstrate

REQUIRED = ["setup","create_member","remove_member","deactivate_member","observe","teardown"]

def test_ha_implements_the_whole_contract():
    for m in REQUIRED:
        assert hasattr(HomeAssistantSubstrate, m), m
        assert callable(getattr(HomeAssistantSubstrate, m))

def test_contract_is_abstract():
    assert inspect.isabstract(Substrate)

def test_capability_vector_keys_are_declared():
    assert set(HomeAssistantSubstrate.CAPABILITIES) == {
        "read","stream","direct_lock","induced_lock","user_enum","event_fire"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_substrate_contract.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'testbed.substrates'`

- [ ] **Step 3: Write minimal implementation**

Create `testbed/substrates/__init__.py` (empty), then:

```python
# testbed/substrates/base.py
from abc import ABC, abstractmethod

class Substrate(ABC):
    """One interface over every platform, so a scenario is written once.

    The cross-platform claim is only as strong as this abstraction: if each
    platform needed its own scenario, a reviewer would have to take on trust
    that the three were equivalent.
    """
    CAPABILITIES = ["read","stream","direct_lock","induced_lock","user_enum","event_fire"]

    @abstractmethod
    def setup(self) -> str: ...
    @abstractmethod
    def create_member(self, name: str, role: str) -> dict: ...
    @abstractmethod
    def remove_member(self, uid: str) -> None: ...
    @abstractmethod
    def deactivate_member(self, uid: str) -> None: ...
    @abstractmethod
    def observe(self, client, devices) -> dict: ...
    @abstractmethod
    def teardown(self) -> None: ...
```

`testbed/substrates/homeassistant.py` copies these already-working helpers from
`experiments/p1e7_matrix.py` unchanged -- they are proven against this platform
and rewriting them would risk a regression the tests would not catch:

| Lift from `p1e7_matrix.py` | Purpose |
|---|---|
| `tokc(s, c)` | exchange an auth code for a token |
| `onboard(s)` | first-run owner creation |
| `login(s, u, p)` | authenticate through the login flow |
| `class C` | WebSocket command/response with id matching |
| `conn(t)` | authenticated socket, returns `(C, status)` |
| `wilson(k, n)` | the interval used everywhere else in the paper |

Then replace the `input_boolean.ts_probe` target with `lock.ts_front_door` and
implement `observe` to return the six-key vector:

```python
async def observe(self, client, devices) -> dict:
    v = {k: False for k in self.CAPABILITIES}
    try:
        r = await client.cmd(type="get_states")
        v["read"] = len(r.get("result") or []) > 0
    except Exception:
        return v                                   # socket dead: nothing available
    v["user_enum"]  = await self._ok(client, type="config/auth/list")
    v["event_fire"] = await self._ok(client, type="fire_event", event_type="ts_probe")
    # direct: command the real lock entity
    await self._owner_set_lock("LOCKED")
    v["direct_lock"] = (await self._ok(client, type="call_service", domain="lock",
                        service="unlock", target={"entity_id": "lock.ts_front_door"})
                        and devices.state("lock.ts_front_door") == "UNLOCKED")
    # induced: fire the event the owner's automation listens for
    await self._owner_set_lock("LOCKED")
    await self._ok(client, type="fire_event", event_type="ts_deputy_trigger")
    await asyncio.sleep(1.5)
    v["induced_lock"] = devices.state("lock.ts_front_door") == "UNLOCKED"
    v["stream"] = await self._stream_delivers(client)
    return v
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_substrate_contract.py -v`
Expected: PASS, 3 passed

- [ ] **Step 5: Commit**

```bash
git add testbed/substrates tests/test_substrate_contract.py
git commit -m "testbed: substrate contract and Home Assistant adapter"
```

---

### Task 3: Client models, including a real browser

**Files:**
- Create: `testbed/clients.py`
- Test: `tests/test_clients.py`

**Interfaces:**
- Produces: `open_client(kind: str, base_url: str, credential: dict) -> Client`
  where `kind` is `"app"`, `"token"` or `"browser"`. `Client` exposes
  `alive() -> bool`, `close() -> None`, and `kind`.
- `ORDINARY_USE` constant documenting the fixed protocol.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_clients.py
from testbed.clients import ORDINARY_USE, KINDS

def test_ordinary_use_is_fixed_and_documented():
    # The measurement is only credible if this cannot be widened later.
    assert ORDINARY_USE["explicit_logout"] is False
    assert ORDINARY_USE["injected_keepalive"] is False
    assert ORDINARY_USE["reconnect_by_us"] is False
    assert ORDINARY_USE["commands_issued"] == 1

def test_three_client_kinds_are_modelled():
    assert set(KINDS) == {"app", "token", "browser"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_clients.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'testbed.clients'`

- [ ] **Step 3: Write minimal implementation**

Install the browser driver first:

```bash
python3 -m pip install playwright && python3 -m playwright install chromium
```

```python
# testbed/clients.py
"""How a household member's device actually holds a connection.

The paper's precondition is a session that exists at the moment of removal. The
point of this module is that we do not create that session by hand: the
`browser` client logs in through the platform's own frontend and then stops
touching it, so whatever connection persists is the product's behaviour, not
ours.
"""
KINDS = ("app", "token", "browser")

# Fixed in advance. Widening any of these to obtain a result is a deviation and
# must be reported as one.
ORDINARY_USE = {
    "authenticate_via_platform_ui": True,
    "view_dashboard": True,
    "commands_issued": 1,
    "explicit_logout": False,
    "injected_keepalive": False,
    "reconnect_by_us": False,
}
```

with `open_client` returning: an `AppClient` (persistent authenticated
WebSocket, platform-native ping only), a `TokenClient` (long-lived access
token), and a `BrowserClient` (Playwright Chromium, real login form, dashboard
left open, then untouched).

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_clients.py -v`
Expected: PASS, 2 passed

- [ ] **Step 5: Commit**

```bash
git add testbed/clients.py tests/test_clients.py
git commit -m "testbed: client models with ordinary-use protocol fixed in code"
```

---

### Task 4: Scenario format and runner

**Files:**
- Create: `testbed/scenario.py`
- Test: `tests/test_scenario.py`

**Interfaces:**
- Consumes: `Substrate` (Task 2), `open_client` (Task 3).
- Produces: `run_scenario(spec: dict, substrate: Substrate) -> dict` returning
  `{"scenario","substrate","pre","post","deviations","precondition_present"}`.
  A scenario spec has keys `name`, `anchor`, `client_kinds`, `transition`,
  `ordinary_use`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_scenario.py
import pytest
from testbed.scenario import validate_spec, run_scenario

def test_spec_requires_a_literature_anchor():
    with pytest.raises(ValueError, match="anchor"):
        validate_spec({"name": "x", "client_kinds": ["app"], "transition": "remove"})

def test_spec_rejects_an_unknown_transition():
    with pytest.raises(ValueError, match="transition"):
        validate_spec({"name":"x","anchor":"freed2018stalker",
                       "client_kinds":["app"],"transition":"teleport"})

def test_runner_records_a_deviation_when_ordinary_use_is_widened():
    spec = {"name":"x","anchor":"freed2018stalker","client_kinds":["app"],
            "transition":"remove","ordinary_use":{"injected_keepalive": True}}
    assert "injected_keepalive" in validate_spec(spec)["deviations"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_scenario.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'testbed.scenario'`

- [ ] **Step 3: Write minimal implementation**

`validate_spec` raises `ValueError` on a missing `anchor`, on a `transition`
outside `{"remove","deactivate","expire","handover"}`, and returns the spec with
a `deviations` list naming every key where `ordinary_use` departs from
`clients.ORDINARY_USE`. `run_scenario` performs setup, creates the member, opens
each client kind, performs ordinary use, records `pre`, applies the transition,
records `post`, and records `precondition_present` per client kind.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_scenario.py -v`
Expected: PASS, 3 passed

- [ ] **Step 5: Commit**

```bash
git add testbed/scenario.py tests/test_scenario.py
git commit -m "testbed: scenario format with anchor and deviation enforcement"
```

---

### Task 5: The four scenarios

**Files:**
- Create: `testbed/scenarios/separation.json`, `roommate.json`,
  `guest_overstay.json`, `handover.json`
- Test: `tests/test_scenario_definitions.py`

**Interfaces:**
- Consumes: `validate_spec` (Task 4).
- Produces: four validated scenario specs on disk.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_scenario_definitions.py
import glob, json
from testbed.scenario import validate_spec

CITED = {"freed2018stalker","matthews2017stories","zeng2019multiuser",
         "tseng2020tools","havron2019clinical"}

def test_every_scenario_validates_and_cites_a_real_reference():
    files = glob.glob("testbed/scenarios/*.json")
    assert len(files) == 4
    for f in files:
        spec = validate_spec(json.load(open(f)))
        assert spec["anchor"] in CITED, f"{f} cites {spec['anchor']}, not in the bibliography"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_scenario_definitions.py -v`
Expected: FAIL, `assert 0 == 4`

- [ ] **Step 3: Write minimal implementation**

```json
// testbed/scenarios/separation.json
{
  "name": "separation",
  "anchor": "freed2018stalker",
  "narrative": "A partner moves out. The household owner removes them from the home. Their phone still has the app installed and was last used that morning.",
  "client_kinds": ["app", "browser", "token"],
  "transition": "remove",
  "role": "administrator"
}
```

with `roommate.json` (`zeng2019multiuser`, role `member`, transition `remove`),
`guest_overstay.json` (`tseng2020tools`, transition `expire`), and
`handover.json` (`matthews2017stories`, transition `handover`).

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_scenario_definitions.py -v`
Expected: PASS, 1 passed

- [ ] **Step 5: Commit**

```bash
git add testbed/scenarios tests/test_scenario_definitions.py
git commit -m "testbed: four household scenarios anchored to cited literature"
```

---

### Task 6: Bring-up and the M1 measurement

**Files:**
- Create: `testbed/compose.yml`, `testbed/run_m1.py`
- Test: `tests/test_m1_reporting.py`

**Interfaces:**
- Consumes: everything above.
- Produces: `results/m1_precondition.json` with, per client kind, `n`,
  `sessions_present`, `proportion`, `wilson_ci`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_m1_reporting.py
from testbed.run_m1 import wilson, summarise

def test_wilson_matches_the_interval_used_elsewhere():
    lo, hi = wilson(30, 30)
    assert round(lo, 3) == 0.886 and round(hi, 3) == 1.000

def test_a_null_result_is_reportable_not_an_error():
    out = summarise({"app": {"n": 30, "present": 0}})
    assert out["app"]["proportion"] == 0.0
    assert out["app"]["reading"].startswith("precondition NOT")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_m1_reporting.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'testbed.run_m1'`

- [ ] **Step 3: Write minimal implementation**

`compose.yml` brings up `eclipse-mosquitto:2` and
`homeassistant/home-assistant:2026.8.3` on one network. `run_m1.py` reuses the
`wilson` function from `experiments/p1e7_matrix.py` verbatim, runs each scenario
across 30 independent trials per client kind, and writes the summary. The
`reading` field says `"precondition NOT the default state"` when the proportion
is below 0.5, so the null result is a first-class output.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_m1_reporting.py -v`
Expected: PASS, 2 passed

- [ ] **Step 5: Commit**

```bash
git add testbed/compose.yml testbed/run_m1.py tests/test_m1_reporting.py
git commit -m "testbed: M1 precondition-prevalence measurement"
```

---

### Task 7: M2 and M3 on a real lock

**Files:**
- Create: `testbed/run_m2_m3.py`
- Modify: `testbed/substrates/homeassistant.py` (add the deputy automation)
- Test: `tests/test_m2_m3.py`

**Interfaces:**
- Produces: `results/m2_capability.json`, `results/m3_composition.json`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_m2_m3.py
from testbed.run_m2_m3 import composition_verdict

def test_composed_when_induced_succeeds_and_direct_fails():
    v = composition_verdict(direct=0, induced=30, n=30)
    assert v["composed"] is True and v["crd"] == 2

def test_not_composed_when_direct_also_succeeds():
    v = composition_verdict(direct=30, induced=30, n=30)
    assert v["composed"] is False and v["crd"] == 1

def test_no_residue_is_not_composition():
    v = composition_verdict(direct=0, induced=0, n=30)
    assert v["composed"] is False and v["crd"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_m2_m3.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'testbed.run_m2_m3'`

- [ ] **Step 3: Write minimal implementation**

```python
def composition_verdict(direct: int, induced: int, n: int) -> dict:
    """Composition requires that the effect be reachable ONLY through the
    multi-carrier path. Direct success means depth 1; no success means no
    residue and composition does not apply."""
    if induced == 0:
        return {"composed": False, "crd": None, "reading": "no actuation residue"}
    if direct > 0:
        return {"composed": False, "crd": 1, "reading": "direct actuation reachable"}
    return {"composed": True, "crd": 2, "reading": "actuation only via the deputy path"}
```

The runner adds an owner-authored automation triggering on an event and calling
`lock.unlock` on `lock.ts_front_door`, then measures direct versus induced
actuation over 30 trials.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_m2_m3.py -v`
Expected: PASS, 3 passed

- [ ] **Step 5: Commit**

```bash
git add testbed/run_m2_m3.py tests/test_m2_m3.py
git commit -m "testbed: M2 capability and M3 composition on a real lock entity"
```

---

### Task 8: openHAB substrate and the SmartThings binding arm

**Files:**
- Create: `testbed/substrates/openhab.py`, `testbed/substrates/smartthings.py`
- Test: `tests/test_smartthings_guardrails.py`

**Interfaces:**
- Produces: `OpenHABSubstrate` implementing `Substrate`;
  `SmartThingsBinding` with `create_devices() -> list[str]`,
  `teardown() -> None`, `assert_safe(device_name: str) -> None`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_smartthings_guardrails.py
import pytest
from testbed.substrates.smartthings import SmartThingsBinding

def test_refuses_to_command_a_device_it_did_not_create():
    b = SmartThingsBinding(token="x", location="y")
    with pytest.raises(PermissionError, match="ts-"):
        b.assert_safe("Living Room Lamp")

def test_allows_only_the_ts_prefix():
    b = SmartThingsBinding(token="x", location="y")
    b.assert_safe("ts-probe-switch")     # must not raise

def test_teardown_targets_only_ts_devices():
    b = SmartThingsBinding(token="x", location="y")
    assert b.teardown_filter()("ts-probe-switch") is True
    assert b.teardown_filter()("Front Door") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_smartthings_guardrails.py -v`
Expected: FAIL, `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# testbed/substrates/smartthings.py
"""SmartThings as a SECONDARY-ECOSYSTEM BINDING, not a revocation substrate.

The public API exposes no location-members endpoint and invitations are
POST-only, so membership revocation cannot be tested here. What SmartThings does
provide is a real cloud device that Home Assistant binds to -- which exercises
the `Binding` carrier the Alloy model has always included and that no experiment
has yet touched at runtime.

SAFETY: this account controls devices in a real home. Only devices this class
created, all `ts-` prefixed, may ever be commanded.
"""
PREFIX = "ts-"

class SmartThingsBinding:
    def __init__(self, token: str, location: str):
        self.token, self.location = token, location
        self._created = []

    def assert_safe(self, device_name: str) -> None:
        if not device_name.startswith(PREFIX):
            raise PermissionError(
                f"refusing to touch {device_name!r}: only {PREFIX}* devices this "
                f"run created may be commanded; the account controls a real home")

    def teardown_filter(self):
        return lambda name: name.startswith(PREFIX)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_smartthings_guardrails.py -v`
Expected: PASS, 3 passed

- [ ] **Step 5: Commit**

```bash
git add testbed/substrates/openhab.py testbed/substrates/smartthings.py tests/test_smartthings_guardrails.py
git commit -m "testbed: openHAB substrate and guarded SmartThings binding arm"
```

---

### Task 8b: M4 cross-platform run

**Files:**
- Create: `testbed/run_m4.py`
- Test: `tests/test_m4_matrix.py`

**Interfaces:**
- Consumes: `HomeAssistantSubstrate`, `OpenHABSubstrate` (Task 8),
  `SmartThingsBinding` (Task 8), `run_scenario` (Task 4).
- Produces: `results/m4_cross_platform.json` keyed
  `[substrate][scenario][capability]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_m4_matrix.py
from testbed.run_m4 import comparable, SUBSTRATES

def test_all_three_substrates_are_registered():
    assert set(SUBSTRATES) == {"home_assistant", "openhab", "smartthings_binding"}

def test_a_capability_a_substrate_cannot_express_is_not_scored_as_clean():
    # SmartThings has no members endpoint, so membership revocation is
    # UNTESTABLE there. Recording that as "no residue" would be a false
    # negative and would overstate the platform's hygiene.
    row = comparable({"user_enum": None}, capability="user_enum")
    assert row["status"] == "untestable"
    assert row["counts_as_clean"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_m4_matrix.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'testbed.run_m4'`

- [ ] **Step 3: Write minimal implementation**

```python
# testbed/run_m4.py
SUBSTRATES = ("home_assistant", "openhab", "smartthings_binding")

def comparable(vector: dict, capability: str) -> dict:
    """A capability the platform cannot express is UNTESTABLE, never clean.

    Scoring an untestable cell as absence of residue would let a platform look
    better than the evidence supports -- the same error as counting a
    capability the principal never held as a closure.
    """
    val = vector.get(capability)
    if val is None:
        return {"status": "untestable", "counts_as_clean": False}
    return {"status": "residual" if val else "closed", "counts_as_clean": not val}
```

Then replay every scenario on every substrate and write the matrix.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_m4_matrix.py -v`
Expected: PASS, 2 passed

- [ ] **Step 5: Commit**

```bash
git add testbed/run_m4.py tests/test_m4_matrix.py
git commit -m "testbed: M4 cross-platform matrix with untestable distinct from clean"
```

---

### Task 9: Paper integration

**Files:**
- Modify: `manuscripts/prj-01m0eedr6pyrhspsg2vf68d7em/IEEE-SP/sections/03_threat.tex`
- Modify: `.../sections/06_determinacy.tex` (compress to buy space)
- Create: `.../sections/07b_evaluation.tex`
- Modify: `.../sections/12_appendix.tex` (ethics: live-systems statement)
- Modify: `.../main.tex` (input the new section)

**Interfaces:**
- Consumes: `results/m1_precondition.json`, `m2_capability.json`,
  `m3_composition.json`.

- [ ] **Step 1: Rewrite §3 so the precondition is measured, not asserted**

Replace "may act through a session established before removal" with a sentence
citing the M1 number and Table for the new Evaluation section.

- [ ] **Step 2: Compress §6 to a half page plus its existing table**

Keep the negative result and `tab:determinacy`; cut the prose around them.

- [ ] **Step 3: Write §7b Evaluation with M1-M4 tables**

- [ ] **Step 4: Correct the ethics section**

The statement "No live or third-party systems... No vendor infrastructure was
contacted" is false once SmartThings runs. Replace with what was actually
touched, the permission basis, the load, and the pre-committed disclosure.

- [ ] **Step 5: Rebuild and re-gate**

Run: `cd manuscripts/prj-01m0eedr6pyrhspsg2vf68d7em/IEEE-SP && latexmk -pdf -interaction=nonstopmode main.tex && python3 check_body_pages.py && python3 check_prohibited.py`
Expected: body <= 13, total <= 18, no prohibited-wording BLOCK.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "paper: measured threat model and testbed evaluation"
```
