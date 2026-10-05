"""P1 EXPERIMENT 21 - configuration auditor re-run with retained output.

Why: the claim that a configuration audit cannot see the residue (writer layer 02,
C-006) rested on one auditor run (2026-09-03, commit 002603f, journal
jrn_01M1JZXH9G05NPZSN4WYRJC046) whose output was not kept. This re-creates the
condition and keeps everything: the auditor's full JSON before and after deletion,
and a probe log showing the residue is live at the moment of the after-audit.

Condition (as C-006 describes it): Home Assistant 2026.8.3 in Docker, an
administrator holding an established WebSocket connection, the owner-authored
deputy automation present (event ts_deputy_trigger -> input_boolean.turn_on), then
deletion of the administrator. Setup follows p1e8d_lifetime_72h.py.

Usage: python3 p1e21_auditor_rerun.py <host-config-dir> <port> <out-prefix>
The container must already be running with <host-config-dir> mounted at /config.
"""
import asyncio, json, os, subprocess, sys, time
import aiohttp, websockets

CFG, PORT, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
BASE = f"http://localhost:{PORT}"; WS = f"ws://localhost:{PORT}/api/websocket"; CID = f"{BASE}/"
OWNER = ("tsowner", "Owner-Passw0rd-123"); PW = "Member-Passw0rd-123"
SUBJ = "auditsubj"; EID = "input_boolean.ts_probe"
AUDITOR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools", "ha_auditor.py")
LOG = open(OUT + "_probe.log", "w")
def log(m):
    line = f"[{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}] {m}"
    print(line, flush=True); LOG.write(line + "\n"); LOG.flush()

async def tokc(s, c):
    async with s.post(f"{BASE}/auth/token", data={"grant_type": "authorization_code", "code": c, "client_id": CID}) as r:
        return await r.json()
async def onboard(s):
    async with s.post(f"{BASE}/api/onboarding/users", json={"client_id": CID, "name": "TS Owner",
            "username": OWNER[0], "password": OWNER[1], "language": "en"}) as r:
        if r.status != 200: return None
        code = (await r.json())["auth_code"]
    t = (await tokc(s, code))["access_token"]
    for st in ("core_config", "analytics"):
        async with s.post(f"{BASE}/api/onboarding/{st}", headers={"Authorization": f"Bearer {t}"}) as r: await r.text()
    return t
async def login(s, u, p):
    async with s.post(f"{BASE}/auth/login_flow", json={"client_id": CID, "handler": ["homeassistant", None],
            "redirect_uri": CID, "type": "authorize"}) as r: f = (await r.json())["flow_id"]
    async with s.post(f"{BASE}/auth/login_flow/{f}", json={"client_id": CID, "username": u, "password": p}) as r:
        j = await r.json()
        if "result" not in j: return None
    return (await tokc(s, j["result"]))["access_token"]

class C:
    """One socket, one permanent reader (the p1e8d fix for max_queue backpressure)."""
    def __init__(s, ws):
        s.ws, s.id, s.pending, s.events, s.dead = ws, 0, {}, [], None
        s.reader = asyncio.create_task(s._read())
    async def _read(s):
        try:
            while True:
                m = json.loads(await s.ws.recv())
                if m.get("type") == "result" and m.get("id") in s.pending:
                    f = s.pending.pop(m["id"])
                    if not f.done(): f.set_result(m)
                else:
                    s.events.append((asyncio.get_event_loop().time(), m))
                    del s.events[:-2048]
        except Exception as e:
            s.dead = e
            for f in s.pending.values():
                if not f.done(): f.set_exception(e)
    async def cmd(s, **kw):
        if s.dead: raise s.dead
        s.id += 1; i = s.id
        f = asyncio.get_event_loop().create_future(); s.pending[i] = f
        await s.ws.send(json.dumps({"id": i, **kw}))
        return await asyncio.wait_for(f, timeout=15)
async def conn(t):
    ws = await websockets.connect(WS, max_size=None, max_queue=512, ping_interval=20, ping_timeout=60, close_timeout=10)
    await ws.recv()
    await ws.send(json.dumps({"type": "auth", "access_token": t})); m = json.loads(await ws.recv())
    return C(ws) if m["type"] == "auth_ok" else None

async def state(c):
    r = await c.cmd(type="get_states")
    for x in (r.get("result") or []):
        if x["entity_id"] == EID: return x["state"]

async def probe(label, m, owner):
    """socket alive / state read / event stream / actuation induced through the owner's automation"""
    v = {"label": label, "time": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
         "socket": False, "read": False, "stream": False, "actuate": False}
    try:
        r = await m.cmd(type="get_states"); v["socket"] = True
        v["read"] = len(r.get("result") or []) > 0
        v["read_entity_count"] = len(r.get("result") or [])
    except Exception as e:
        v["exception"] = f"{type(e).__name__}: {e}"
        log(f"  {label:30s} 0/0/0/0 (socket dead: {v['exception']})"); return v
    t0 = asyncio.get_event_loop().time()
    await owner.cmd(type="call_service", domain="input_boolean", service="toggle", target={"entity_id": EID})
    await asyncio.sleep(1.8)
    v["stream"] = any(t >= t0 and e.get("type") == "event" for t, e in list(m.events))
    await owner.cmd(type="call_service", domain="input_boolean", service="turn_off", target={"entity_id": EID})
    await asyncio.sleep(0.6)
    v["state_before_fire"] = await state(owner)
    fr = await m.cmd(type="fire_event", event_type="ts_deputy_trigger")
    v["fire_event_success"] = bool(fr.get("success"))
    await asyncio.sleep(1.6)
    v["state_after_fire"] = await state(owner)
    v["actuate"] = v["state_before_fire"] == "off" and v["state_after_fire"] == "on"
    log(f"  {label:30s} {int(v['socket'])}/{int(v['read'])}/{int(v['stream'])}/{int(v['actuate'])}"
        f"   (fire_event success={v['fire_event_success']}, {v['state_before_fire']} -> {v['state_after_fire']})")
    return v

def audit(tag, principal):
    out = subprocess.run([sys.executable, AUDITOR, CFG, "--principal", principal, "--json"],
                         capture_output=True, text=True)
    txt = subprocess.run([sys.executable, AUDITOR, CFG, "--principal", principal],
                         capture_output=True, text=True)
    with open(f"{OUT}_{tag}.json", "w") as f: f.write(out.stdout)
    with open(f"{OUT}_{tag}.txt", "w") as f: f.write(txt.stdout + (("\nSTDERR:\n" + txt.stderr) if txt.stderr else ""))
    r = json.loads(out.stdout)
    log(f"  AUDIT {tag:7s} principal={principal} resolved={r['resolved_user_id']} named={len(r['named'])} "
        f"carriers={len(r['carriers'])} unseen={len(r['unseen'])}")
    for k, i, n in r["named"]: log(f"      named  {k:14s} {i}  {n}")
    return r

async def main():
    log(f"P1E21 auditor re-run; HA image homeassistant/home-assistant:2026.8.3; port {PORT}; config {CFG}")
    log(f"python {sys.version.split()[0]}, websockets {websockets.__version__}, aiohttp {aiohttp.__version__}")
    rows = []
    async with aiohttp.ClientSession() as s:
        otok = await onboard(s) or await login(s, *OWNER)
        owner = await conn(otok)
        try: await owner.cmd(type="input_boolean/create", name="ts probe")
        except Exception: pass
        await asyncio.sleep(1.2)
        H = {"Authorization": f"Bearer {otok}", "Content-Type": "application/json"}
        async with s.post(f"{BASE}/api/config/automation/config/tsdeputy", headers=H,
                json={"alias": "ts deputy probe", "trigger": [{"platform": "event", "event_type": "ts_deputy_trigger"}],
                      "action": [{"service": "input_boolean.turn_on", "target": {"entity_id": EID}}], "mode": "single"}) as r2:
            log(f"  owner-authored deputy automation saved: HTTP {r2.status}")
        await owner.cmd(type="call_service", domain="automation", service="reload"); await asyncio.sleep(2)
        r = await owner.cmd(type="config/auth/create", name="audit subj", group_ids=["system-admin"], local_only=False)
        uid = r["result"]["user"]["id"]
        await owner.cmd(type="config/auth_provider/homeassistant/create", user_id=uid, username=SUBJ, password=PW)
        mtok = await login(s, SUBJ, PW)
        m = await conn(mtok)
        await m.cmd(type="subscribe_events", event_type="state_changed"); await asyncio.sleep(0.5)
        log(f"  subject {SUBJ} created in system-admin (user_id {uid}); websocket established and subscribed")
        rows.append(await probe("pre-deletion control", m, owner))
        await asyncio.sleep(12)            # let the delayed .storage writes land before reading the files
        before = audit("before", uid)
        await owner.cmd(type="config/auth/delete", user_id=uid)
        log("  subject DELETED (config/auth/delete)")
        await asyncio.sleep(12)            # same flush wait after the deletion
        rows.append(await probe("after deletion, before audit", m, owner))
        after = audit("after", uid)
        after_name = audit("after_by_name", SUBJ)
        rows.append(await probe("after deletion, after audit", m, owner))
        json.dump({"rows": rows, "subject_user_id": uid,
                   "audit_before_named": len(before["named"]), "audit_after_named": len(after["named"]),
                   "audit_after_by_name_named": len(after_name["named"])},
                  open(OUT + "_probe.json", "w"), indent=1)
        log("DONE")

asyncio.run(main())
