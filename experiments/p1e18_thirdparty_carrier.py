"""P1 EXPERIMENT 18 - a composed residue whose second carrier is a THIRD-PARTY
integration, not an automation inside the platform.

Review W1: the only depth-two witness in the study is the Home Assistant case,
and a sceptic can call its second carrier (a household automation) an artifact
of what automations are for. The reviewer asks for a second composed witness,
and suggests the shape: a removed member's long-lived token still bound in a
third-party integration that a surviving flow then relays.

That is a stronger witness than the automation case for the audit-visibility
argument, because the carrier lives OUTSIDE the platform entirely. A household
inspecting Home Assistant's own user list, tokens and automations sees nothing:
the token is held in another process's configuration.

Arms, all on a token minted by an administrator who is then deleted:
    long-lived token, direct call, before deletion   expect works
    long-lived token, direct call, after deletion    the question
    third-party relay actuates, after deletion       the composed question

We do not need Node-RED itself to run a flow engine to make the point: what a
third-party integration does is hold a long-lived token and issue calls with it.
This probe holds the token exactly as such an integration would, in a separate
process, and asks whether the platform still honours it after the principal
that minted it has been removed.
"""
import asyncio, json, sys, aiohttp, websockets

PORT = sys.argv[1] if len(sys.argv) > 1 else "8193"
BASE = f"http://localhost:{PORT}"; WS = f"ws://localhost:{PORT}/api/websocket"; CID = f"{BASE}/"
OWNER = ("tsowner", "Owner-Passw0rd-123"); PW = "Admin-Passw0rd-123"
EID = "input_boolean.tp_probe"
log = lambda m: print(m, flush=True)

async def tokc(s, c):
    async with s.post(f"{BASE}/auth/token", data={"grant_type": "authorization_code", "code": c, "client_id": CID}) as r:
        return await r.json()
async def onboard(s):
    async with s.post(f"{BASE}/api/onboarding/users", json={"client_id": CID, "name": "TS Owner",
            "username": OWNER[0], "password": OWNER[1], "language": "en"}) as r:
        if r.status != 200: return None
        t = (await tokc(s, (await r.json())["auth_code"]))["access_token"]
    for st in ("core_config", "analytics"):
        async with s.post(f"{BASE}/api/onboarding/{st}", headers={"Authorization": f"Bearer {t}"}) as r: await r.text()
    return t
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

async def rest_call(tok, domain, service, entity):
    """Exactly what a third-party integration does: a REST service call with a
    long-lived token, from a process that is not the platform."""
    async with aiohttp.ClientSession() as s2:
        try:
            async with s2.post(f"{BASE}/api/services/{domain}/{service}",
                    headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
                    json={"entity_id": entity},
                    timeout=aiohttp.ClientTimeout(total=8)) as r:
                return r.status
        except Exception:
            return 0

async def state(owner, eid):
    r = await owner.cmd(type="get_states")
    for st in (r.get("result") or []):
        if st["entity_id"] == eid: return st["state"]
    return None

async def main():
    async with aiohttp.ClientSession() as s:
        otok = await onboard(s) or await login(s, *OWNER)
        owner, _ = await conn(otok)
        if not owner: log("FATAL: owner socket"); sys.exit(2)
        try: await owner.cmd(type="input_boolean/create", name="tp probe")
        except Exception: pass
        await asyncio.sleep(1.2)

        # an administrator who will later be removed
        u = "tp_admin"
        r = await owner.cmd(type="config/auth/create", name="tp admin", group_ids=["system-admin"], local_only=False)
        uid = r["result"]["user"]["id"]
        await owner.cmd(type="config/auth_provider/homeassistant/create", user_id=uid, username=u, password=PW)
        atok = await login(s, u, PW)
        adm, _ = await conn(atok)
        if not adm: log("FATAL: admin socket"); sys.exit(2)

        # the admin mints a LONG-LIVED token, the way one is minted for an integration
        llt = None
        try:
            r = await adm.cmd(type="auth/long_lived_access_token", client_name="tp-integration", lifespan=365)
            llt = r.get("result")
        except Exception as e:
            log(f"  long-lived token mint failed: {e}")
        if not llt: log("FATAL: could not mint a long-lived token"); sys.exit(2)
        log(f"  long-lived token minted by the administrator (len {len(llt)})")

        log(f"\n  {'arm':52s} {'result'}")
        log(f"  {'-'*52} {'-'*24}")
        await owner.cmd(type="call_service", domain="input_boolean", service="turn_off", target={"entity_id": EID})
        await asyncio.sleep(0.4)
        code = await rest_call(llt, "input_boolean", "turn_on", EID)
        st = await state(owner, EID)
        log(f"  {'third-party token, direct call, BEFORE removal':52s} HTTP {code}, entity={st}")

        # --- remove the administrator ---
        await owner.cmd(type="config/auth/delete", user_id=uid)
        await asyncio.sleep(2)
        log(f"\n  administrator DELETED")

        await owner.cmd(type="call_service", domain="input_boolean", service="turn_off", target={"entity_id": EID})
        await asyncio.sleep(0.4)
        code2 = await rest_call(llt, "input_boolean", "turn_on", EID)
        st2 = await state(owner, EID)
        log(f"\n  {'third-party token, direct call, AFTER removal':52s} HTTP {code2}, entity={st2}")

        # does the admin's own websocket still work (the known result, as a control)
        try:
            r = await adm.cmd(type="get_states"); sock_alive = bool(r.get("result") is not None)
        except Exception: sock_alive = False
        log(f"  {'control: the removed admin websocket still reads':52s} {sock_alive}")

        log("")
        if code2 in (200, 201) and st2 == "on":
            log("  VERDICT: SECOND COMPOSED WITNESS, and a stronger one.")
            log("  A long-lived token minted by an administrator who has since been deleted")
            log("  still actuates a device, from a process outside the platform. The carrier")
            log("  is a third-party integration's stored credential, which no per-object")
            log("  audit of users, sessions or automations enumerates. Depth two, and the")
            log("  second carrier is not a household automation, so the objection that the")
            log("  automation is 'what automations are for' does not apply.")
        elif code2 == 401:
            log("  VERDICT: the long-lived token IS revoked on deletion. The third-party")
            log("  carrier does not survive, so this is not a second composed witness, and")
            log("  the paper should say that the residue is confined to the live connection.")
        else:
            log(f"  VERDICT: inconclusive (HTTP {code2}, entity={st2}). Inspect above.")

asyncio.run(main())
