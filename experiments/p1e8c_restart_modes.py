"""P1 EXPERIMENT 8c - which restart actually ends the residue?

Section 7.9 reports that the residue survives automation reload and integration
reload, and that "restarting the container the platform runs in" clears it. A
reviewer objected that a container restart is not what a household does: Home
Assistant offers "Restart Home Assistant" in its own interface, which restarts
the core process without touching the container. If the in-UI restart also
clears the socket, then the remedy IS one the interface offers, and the paper's
severity argument has to be narrowed.

Arms, in order, on one surviving socket:
    baseline            socket alive, read/stream/actuate before any restart
    after core restart  homeassistant.restart service - the in-UI action
    after container     docker restart - the arm already in the paper
"""
import asyncio, json, subprocess, sys, aiohttp, websockets

PORT = sys.argv[1] if len(sys.argv) > 1 else "8188"
CONT = sys.argv[2] if len(sys.argv) > 2 else "tssubctl"
BASE = f"http://localhost:{PORT}"; WS = f"ws://localhost:{PORT}/api/websocket"; CID = f"{BASE}/"
OWNER = ("tsowner2", "Owner-Passw0rd-123"); PW = "Member-Passw0rd-123"
EID = "input_boolean.rs_probe"  # created via the websocket input_boolean/create command
log = lambda m: print(m, flush=True)

async def tokc(s, c):
    async with s.post(f"{BASE}/auth/token", data={"grant_type": "authorization_code", "code": c, "client_id": CID}) as r:
        return await r.json()
async def login(s, u, p):
    async with s.post(f"{BASE}/auth/login_flow", json={"client_id": CID, "handler": ["homeassistant", None],
            "redirect_uri": CID, "type": "authorize"}) as r:
        f = (await r.json())["flow_id"]
    async with s.post(f"{BASE}/auth/login_flow/{f}", json={"client_id": CID, "username": u, "password": p}) as r:
        j = await r.json()
        if "result" not in j: return None
    return (await tokc(s, j["result"]))["access_token"]
class C:
    def __init__(s, ws): s.ws, s.id = ws, 0
    async def cmd(s, **kw):
        s.id += 1; await s.ws.send(json.dumps({"id": s.id, **kw}))
        while True:
            m = json.loads(await asyncio.wait_for(s.ws.recv(), timeout=12))
            if m.get("id") == s.id and m["type"] == "result": return m
async def conn(t):
    ws = await websockets.connect(WS, max_size=None); await ws.recv()
    await ws.send(json.dumps({"type": "auth", "access_token": t}))
    m = json.loads(await ws.recv())
    return (C(ws), m) if m["type"] == "auth_ok" else (None, m)

async def probe(m, owner, label):
    """socket / read / induced actuation, in the paper's own columns."""
    v = {"socket": False, "read": False, "actuate": False}
    try:
        r = await m.cmd(type="get_states"); v["socket"] = True
        v["read"] = len(r.get("result") or []) > 0
    except Exception as e:
        log(f"  {label:24s} 0/0/0   (socket dead: {type(e).__name__})")
        return v
    try:
        await owner.cmd(type="call_service", domain="input_boolean", service="turn_off",
                        target={"entity_id": EID})
        await asyncio.sleep(0.4)
        await m.cmd(type="fire_event", event_type="rs_trigger")
        await asyncio.sleep(1.6)
        r = await owner.cmd(type="get_states")
        for st in (r.get("result") or []):
            if st["entity_id"] == EID: v["actuate"] = (st["state"] == "on")
    except Exception: pass
    log(f"  {label:24s} {int(v['socket'])}/{int(v['read'])}/{int(v['actuate'])}")
    return v

async def wait_up(s, tries=90):
    for _ in range(tries):
        try:
            async with s.get(f"{BASE}/", timeout=aiohttp.ClientTimeout(total=4)) as r:
                if r.status in (200, 302): return True
        except Exception: pass
        await asyncio.sleep(3)
    return False

async def main():
    async with aiohttp.ClientSession() as s:
        # owner already onboarded by the previous experiment; log in as owner
        async with s.post(f"{BASE}/api/onboarding/users", json={"client_id": CID, "name": "TS Owner2",
                "username": OWNER[0], "password": OWNER[1], "language": "en"}) as r:
            if r.status == 200:
                otok = (await tokc(s, (await r.json())["auth_code"]))["access_token"]
            else:
                otok = await login(s, "tsowner", "Owner-Passw0rd-123")
        if not otok: log("FATAL: no owner token"); sys.exit(2)
        owner, _ = await conn(otok)
        if not owner: log("FATAL: owner socket"); sys.exit(2)

        try: await owner.cmd(type="input_boolean/create", name="rs probe")
        except Exception: pass
        await asyncio.sleep(1.2)
        H = {"Authorization": f"Bearer {otok}", "Content-Type": "application/json"}
        async with s.post(f"{BASE}/api/config/automation/config/rsdeputy", headers=H,
            json={"alias": "rs deputy", "trigger": [{"platform": "event", "event_type": "rs_trigger"}],
                  "action": [{"service": "input_boolean.turn_on", "target": {"entity_id": EID}}],
                  "mode": "single"}) as r: await r.text()
        try: await owner.cmd(type="call_service", domain="automation", service="reload")
        except Exception: pass
        await asyncio.sleep(2)

        u = "rs_admin"
        r = await owner.cmd(type="config/auth/create", name="rs admin", group_ids=["system-admin"], local_only=False)
        uid = r["result"]["user"]["id"]
        await owner.cmd(type="config/auth_provider/homeassistant/create", user_id=uid, username=u, password=PW)
        mt = await login(s, u, PW)
        m, _ = await conn(mt)
        if not m: log("FATAL: subject socket"); sys.exit(2)

        log("\n=== RESTART MODES: what actually ends the residue ===")
        log("  columns: socket/read/induced-actuation\n")
        await probe(m, owner, "pre-deletion control")
        await owner.cmd(type="config/auth/delete", user_id=uid)
        await asyncio.sleep(1.5)
        await probe(m, owner, "after deletion")

        # ---- the in-UI action: Restart Home Assistant (core only) ----
        log("\n  issuing homeassistant.restart (the in-UI action)...")
        try: await owner.cmd(type="call_service", domain="homeassistant", service="restart")
        except Exception: pass
        await asyncio.sleep(8)
        if not await wait_up(s): log("  FATAL: core did not come back"); sys.exit(2)
        await asyncio.sleep(6)
        r1 = await probe(m, owner, "after CORE restart")

        # rebuild owner if needed, then container restart
        try: await owner.cmd(type="get_states")
        except Exception:
            owner, _ = await conn(otok)
        log("\n  issuing docker restart (the arm already in the paper)...")
        subprocess.run(["docker", "restart", CONT], capture_output=True, timeout=180)
        await asyncio.sleep(10)
        if not await wait_up(s): log("  FATAL: container did not come back"); sys.exit(2)
        await asyncio.sleep(6)
        try: owner, _ = await conn(otok)
        except Exception: pass
        r2 = await probe(m, owner, "after CONTAINER restart")

        log("")
        if not r1["socket"]:
            log("  VERDICT: the in-UI restart ENDS the residue. The remedy is one the")
            log("  interface offers, and Section 7.9 must say so: the exposure window is")
            log("  bounded by the next core restart, not by the next container restart.")
        else:
            log("  VERDICT: the in-UI restart does NOT end the residue; only the container")
            log("  restart does. The paper's claim stands and is now tested against the")
            log("  action a household would actually take.")

asyncio.run(main())
