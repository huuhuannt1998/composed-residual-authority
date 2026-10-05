"""P1 EXPERIMENT 7c - is the member's new-subscription denial caused by removal,
or by the role the member already had?

Table 7 reports new_subscribe 0/30 for a deleted member and 30/30 for a deleted
administrator, and a reviewer asked why subscription creation should depend on
role. Reading commands.py:194 suggests it does not depend on removal at all:

    if event_type not in SUBSCRIBE_ALLOWLIST and not connection.user.is_admin:
        raise Unauthorized(user_id=connection.user.id)

SUBSCRIBE_ALLOWLIST is a fixed set of system event types. The probe subscribes
to a custom event, so a NON-DELETED member should be refused exactly as a
deleted one is. If that holds, the 0/30 cell measures the member's role, not
the transition, and its pre-transition control was never like-for-like: the
pre value was copied from a state_changed subscription (matrix.py:78).

Four arms, each on a fresh member and a fresh admin:
    live member  -> custom event        expect REFUSED   (role, not removal)
    live member  -> state_changed       expect ALLOWED   (in the allowlist)
    deleted member -> custom event      expect REFUSED   (same as live)
    live admin   -> custom event        expect ALLOWED   (admin bypasses)
"""
import asyncio, json, sys, aiohttp, websockets

PORT = sys.argv[1] if len(sys.argv) > 1 else "8123"
BASE = f"http://localhost:{PORT}"; WS = f"ws://localhost:{PORT}/api/websocket"; CID = f"{BASE}/"
OWNER = ("tsowner", "Owner-Passw0rd-123"); PW = "Member-Passw0rd-123"
REPS = int(sys.argv[2]) if len(sys.argv) > 2 else 5
log = lambda m: print(m, flush=True)

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
        async with s.post(f"{BASE}/api/onboarding/{st}", headers={"Authorization": f"Bearer {t}"}) as r:
            await r.text()
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

async def try_subscribe(c, event_type):
    """Returns (accepted, error_code)."""
    try:
        r = await c.cmd(type="subscribe_events", event_type=event_type)
        return bool(r.get("success")), (r.get("error") or {}).get("code")
    except Exception as e:
        return False, type(e).__name__

async def main():
    async with aiohttp.ClientSession() as s:
        otok = await onboard(s)
        if not otok: log("FATAL: onboarding failed"); sys.exit(2)
        owner, _ = await conn(otok)
        if not owner: log("FATAL: owner socket failed"); sys.exit(2)

        arms = {k: {"ok": 0, "n": 0, "errs": set()} for k in
                ("live_member_custom", "live_member_state_changed", "deleted_member_custom", "live_admin_custom")}

        for i in range(REPS):
            # --- member, still live ---
            u = f"sc_member_{i}".lower()
            r = await owner.cmd(type="config/auth/create", name=f"sc m{i}", group_ids=["system-users"], local_only=False)
            uid = r["result"]["user"]["id"]
            await owner.cmd(type="config/auth_provider/homeassistant/create", user_id=uid, username=u, password=PW)
            mt = await login(s, u, PW)
            m, _ = await conn(mt)
            if m:
                ok, err = await try_subscribe(m, "sc_custom_probe")
                arms["live_member_custom"]["n"] += 1; arms["live_member_custom"]["ok"] += ok
                if err: arms["live_member_custom"]["errs"].add(str(err))
                ok2, err2 = await try_subscribe(m, "state_changed")
                arms["live_member_state_changed"]["n"] += 1; arms["live_member_state_changed"]["ok"] += ok2
                if err2: arms["live_member_state_changed"]["errs"].add(str(err2))
                # now delete the same member and retry the custom subscribe on the SAME socket
                await owner.cmd(type="config/auth/delete", user_id=uid)
                await asyncio.sleep(1.2)
                ok3, err3 = await try_subscribe(m, "sc_custom_probe2")
                arms["deleted_member_custom"]["n"] += 1; arms["deleted_member_custom"]["ok"] += ok3
                if err3: arms["deleted_member_custom"]["errs"].add(str(err3))

            # --- admin, still live ---
            ua = f"sc_admin_{i}".lower()
            r = await owner.cmd(type="config/auth/create", name=f"sc a{i}", group_ids=["system-admin"], local_only=False)
            uida = r["result"]["user"]["id"]
            await owner.cmd(type="config/auth_provider/homeassistant/create", user_id=uida, username=ua, password=PW)
            at = await login(s, ua, PW)
            a, _ = await conn(at)
            if a:
                ok4, err4 = await try_subscribe(a, "sc_custom_probe")
                arms["live_admin_custom"]["n"] += 1; arms["live_admin_custom"]["ok"] += ok4
                if err4: arms["live_admin_custom"]["errs"].add(str(err4))
                await a.ws.close()
            await owner.cmd(type="config/auth/delete", user_id=uida)

        log("\n=== SUBSCRIBE CONTROL: role restriction vs removal effect ===\n")
        log(f"  {'arm':32s} {'accepted':>10s}  error code(s)")
        for k in ("live_member_custom", "live_member_state_changed", "deleted_member_custom", "live_admin_custom"):
            v = arms[k]
            log(f"  {k:32s} {v['ok']:>4d}/{v['n']:<5d}  {','.join(sorted(v['errs'])) or '-'}")

        lm = arms["live_member_custom"]; dm = arms["deleted_member_custom"]
        lsc = arms["live_member_state_changed"]; la = arms["live_admin_custom"]
        log("")
        if lm["ok"] == 0 and dm["ok"] == 0 and lsc["ok"] == lsc["n"] and la["ok"] == la["n"]:
            log("  VERDICT: the denial is the ROLE, not the removal.")
            log("  A live member is refused a custom event type exactly as a deleted one is,")
            log("  while the same live member is allowed state_changed and an admin is allowed")
            log("  the custom type. Table 7's member new_subscribe cell therefore measures a")
            log("  pre-existing role restriction, and its pre-transition control was taken on a")
            log("  different operation (state_changed), so it was never like-for-like.")
        else:
            log("  VERDICT: NOT the simple role explanation. Inspect the per-arm counts above.")

asyncio.run(main())
