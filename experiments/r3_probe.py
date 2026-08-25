"""
TENANTSAFE Stage 7 — R3 confirmation.
Q: after a user is REMOVED, does their already-open authenticated WebSocket
   still service commands?  Control arm: DEACTIVATE, which per source fires
   revoke callbacks and should cancel the connection.
"""
import asyncio, json, sys
import aiohttp, websockets

BASE = "http://localhost:8124"
WS   = "ws://localhost:8124/api/websocket"
CID  = "http://localhost:8124/"
OWNER = ("tsowner", "Owner-Passw0rd-123")

log = lambda m: print(m, flush=True)

async def token_from_code(s, code):
    async with s.post(f"{BASE}/auth/token", data={
        "grant_type": "authorization_code", "code": code, "client_id": CID}) as r:
        return (await r.json())["access_token"]

async def onboard(s):
    async with s.post(f"{BASE}/api/onboarding/users", json={
        "client_id": CID, "name": "TS Owner", "username": OWNER[0],
        "password": OWNER[1], "language": "en"}) as r:
        if r.status != 200:
            raise SystemExit(f"onboard failed {r.status}: {await r.text()}")
        code = (await r.json())["auth_code"]
    tok = await token_from_code(s, code)
    for step in ("core_config", "analytics"):
        async with s.post(f"{BASE}/api/onboarding/{step}",
                          headers={"Authorization": f"Bearer {tok}"}) as r:
            await r.text()
    return tok

async def user_login(s, username, password):
    async with s.post(f"{BASE}/auth/login_flow", json={
        "client_id": CID, "handler": ["homeassistant", None],
        "redirect_uri": CID, "type": "authorize"}) as r:
        flow = (await r.json())["flow_id"]
    async with s.post(f"{BASE}/auth/login_flow/{flow}", json={
        "client_id": CID, "username": username, "password": password}) as r:
        j = await r.json()
        if "result" not in j:
            raise SystemExit(f"login failed: {j}")
        code = j["result"]
    return await token_from_code(s, code)

class Conn:
    def __init__(self, ws): self.ws, self.id = ws, 0
    async def cmd(self, **kw):
        self.id += 1
        await self.ws.send(json.dumps({"id": self.id, **kw}))
        while True:
            m = json.loads(await asyncio.wait_for(self.ws.recv(), timeout=15))
            if m.get("id") == self.id and m["type"] == "result":
                return m

async def connect(token):
    ws = await websockets.connect(WS, max_size=None)
    assert json.loads(await ws.recv())["type"] == "auth_required"
    await ws.send(json.dumps({"type": "auth", "access_token": token}))
    msg = json.loads(await ws.recv())
    if msg["type"] != "auth_ok":
        await ws.close(); return None, msg
    return Conn(ws), msg

async def state_of(conn, eid):
    r = await conn.cmd(type="get_states")
    for s in r["result"]:
        if s["entity_id"] == eid: return s["state"]
    return None

async def arm(owner, s, label, uname, mode, eid):
    """mode: 'delete' | 'deactivate'"""
    log(f"\n{'='*66}\nARM: {label}\n{'='*66}")
    r = await owner.cmd(type="config/auth/create", name=f"TS {label}",
                        group_ids=["system-users"], local_only=False)
    uid = r["result"]["user"]["id"]
    await owner.cmd(type="config/auth_provider/homeassistant/create",
                    user_id=uid, username=uname, password="Member-Passw0rd-123")
    log(f"  created member user_id={uid}")

    tok = await user_login(s, uname, "Member-Passw0rd-123")
    conn, _ = await connect(tok)
    log("  member WebSocket authenticated (auth_ok)")

    await owner.cmd(type="call_service", domain="input_boolean",
                    service="turn_off", target={"entity_id": eid})
    r = await conn.cmd(type="call_service", domain="input_boolean",
                       service="turn_on", target={"entity_id": eid})
    pre = await state_of(owner, eid)
    log(f"  CONTROL (pre-{mode}): success={r['success']} state={pre}")
    if not (r["success"] and pre == "on"):
        raise SystemExit("control arm failed — member could not act BEFORE removal")

    await owner.cmd(type="call_service", domain="input_boolean",
                    service="turn_off", target={"entity_id": eid})

    if mode == "delete":
        d = await owner.cmd(type="config/auth/delete", user_id=uid)
    else:
        d = await owner.cmd(type="config/auth/update", user_id=uid, is_active=False)
    log(f"  {mode} issued: success={d['success']}")
    await asyncio.sleep(2.0)

    # THE TEST: same still-open socket, after policy says the principal is gone
    verdict = {}
    try:
        r2 = await conn.cmd(type="call_service", domain="input_boolean",
                            service="turn_on", target={"entity_id": eid})
        post = await state_of(owner, eid)
        verdict["open_socket"] = ("SERVICED" if (r2.get("success") and post == "on")
                                  else f"refused({r2.get('error')})")
        verdict["entity_state"] = post
    except (websockets.ConnectionClosed, asyncio.TimeoutError) as e:
        verdict["open_socket"] = f"CONNECTION CLOSED ({type(e).__name__})"
        verdict["entity_state"] = await state_of(owner, eid)

    nc, why = await connect(tok)
    verdict["new_connection"] = "ACCEPTED" if nc else f"rejected({why.get('type')})"
    if nc: await nc.ws.close()
    try: await conn.ws.close()
    except Exception: pass
    log(f"  RESULT open-socket : {verdict['open_socket']}")
    log(f"  RESULT entity state: {verdict['entity_state']}")
    log(f"  RESULT new conn    : {verdict['new_connection']}")
    return verdict

async def main():
    async with aiohttp.ClientSession() as s:
        log("onboarding owner...")
        otok = await onboard(s)
        owner, _ = await connect(otok)
        log("owner WebSocket authenticated")
        eid = "input_boolean.ts_probe"
        try:
            await owner.cmd(type="input_boolean/create", name="ts probe")
        except Exception as e:
            log(f"  helper create note: {e}")
        await asyncio.sleep(1.5)
        if await state_of(owner, eid) is None:
            raise SystemExit(f"{eid} not created")
        log(f"probe entity ready: {eid}")

        a = await arm(owner, s, "R3 TEST — user REMOVED", "member_del", "delete", eid)
        b = await arm(owner, s, "CONTROL — user DEACTIVATED", "member_deact", "deactivate", eid)

        log("\n" + "="*66 + "\nSUMMARY\n" + "="*66)
        log(f"  REMOVED    : open socket -> {a['open_socket']:<32} new conn -> {a['new_connection']}")
        log(f"  DEACTIVATED: open socket -> {b['open_socket']:<32} new conn -> {b['new_connection']}")
        residue = a["open_socket"] == "SERVICED"
        ctrl_ok = "CLOSED" in b["open_socket"] or "refused" in b["open_socket"]
        log("")
        log(f"  R3 CONFIRMED: {residue and ctrl_ok}   (residue={residue}, control_differs={ctrl_ok})")
        json.dump({"removed": a, "deactivated": b, "r3_confirmed": residue and ctrl_ok},
                  open("/config_out.json", "w") if False else sys.stderr)

asyncio.run(main())
