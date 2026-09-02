"""
E7.6 — THE DEPUTY TEST on Home Assistant (L3).
Q: after a user is removed, can their orphaned socket still cause ACTUATION
   indirectly, by firing an event that triggers a household automation?
   Direct call_service is blocked (UnknownUser, E7.3). The deputy path routes
   authority through the automation instead.
Also E7.8: long-lived access token behaviour across removal vs deactivation.
"""
import asyncio, json
import aiohttp, websockets

BASE="http://localhost:8124"; WS="ws://localhost:8124/api/websocket"; CID="http://localhost:8124/"
OWNER=("tsowner","Owner-Passw0rd-123"); PW="Member-Passw0rd-123"
EID="input_boolean.ts_probe"
log=lambda m: print(m, flush=True)

async def tok_from_code(s,c):
    async with s.post(f"{BASE}/auth/token", data={"grant_type":"authorization_code","code":c,"client_id":CID}) as r:
        return await r.json()
async def onboard(s):
    """The runner supplies a FRESH instance, so create the owner rather than
    assuming one exists. Logging in blind against a clean container fails with
    invalid_auth, which reads as an auth defect rather than missing setup."""
    async with s.post(f"{BASE}/api/onboarding/users",json={"client_id":CID,"name":"TS Owner",
        "username":OWNER[0],"password":OWNER[1],"language":"en"}) as r:
        if r.status!=200: return None
        code=(await r.json())["auth_code"]
    t=(await tok_from_code(s,code))["access_token"]
    for st in ("core_config","analytics"):
        async with s.post(f"{BASE}/api/onboarding/{st}",headers={"Authorization":f"Bearer {t}"}) as r:
            await r.text()
    return t

async def login(s,u,p):
    async with s.post(f"{BASE}/auth/login_flow", json={"client_id":CID,"handler":["homeassistant",None],"redirect_uri":CID,"type":"authorize"}) as r:
        f=(await r.json())["flow_id"]
    async with s.post(f"{BASE}/auth/login_flow/{f}", json={"client_id":CID,"username":u,"password":p}) as r:
        j=await r.json()
        if "result" not in j: raise SystemExit(f"login failed {u}: {j}")
    return await tok_from_code(s,j["result"])

class C:
    def __init__(s,ws): s.ws,s.id=ws,0
    async def cmd(s,**kw):
        s.id+=1; await s.ws.send(json.dumps({"id":s.id,**kw}))
        while True:
            m=json.loads(await asyncio.wait_for(s.ws.recv(),timeout=15))
            if m.get("id")==s.id and m["type"]=="result": return m
async def conn(t):
    ws=await websockets.connect(WS,max_size=None); await ws.recv()
    await ws.send(json.dumps({"type":"auth","access_token":t}))
    m=json.loads(await ws.recv())
    return (C(ws),m) if m["type"]=="auth_ok" else (None,m)
async def state(c,eid):
    r=await c.cmd(type="get_states")
    for s in r["result"]:
        if s["entity_id"]==eid: return s["state"]
    return None

async def main():
    async with aiohttp.ClientSession() as s:
        otok=await onboard(s) or (await login(s,*OWNER))["access_token"]
        owner,_=await conn(otok); log("owner connected")
        # These scripts were written against an instance where an earlier
        # experiment had already created the probe entity. On a fresh container
        # it does not exist, actuation cannot be observed, and the result reads
        # as "no residue" rather than "no measurement". Create it here.
        try: await owner.cmd(type="input_boolean/create",name="ts probe")
        except Exception: pass
        await asyncio.sleep(1.2)

        # --- install a household automation triggered by a custom event ---
        auto={"alias":"ts deputy probe","trigger":[{"platform":"event","event_type":"ts_deputy_trigger"}],
              "action":[{"service":"input_boolean.turn_on","target":{"entity_id":EID}}],"mode":"single"}
        async with s.post(f"{BASE}/api/config/automation/config/tsdeputy",
                          headers={"Authorization":f"Bearer {otok}","Content-Type":"application/json"},
                          json=auto) as r:
            log(f"  automation installed: HTTP {r.status}")
        await owner.cmd(type="call_service",domain="automation",service="reload")
        await asyncio.sleep(2)

        # --- member creates + authenticates ---
        r=await owner.cmd(type="config/auth/create",name="TS Deputy Admin",group_ids=["system-admin"],local_only=False)
        uid=r["result"]["user"]["id"]
        await owner.cmd(type="config/auth_provider/homeassistant/create",user_id=uid,username="member_dep2",password=PW)
        mtokens=await login(s,"member_dep2",PW)
        mtok=mtokens["access_token"]
        m,_=await conn(mtok); log(f"  member connected (uid={uid})")

        # E7.8 — mint a long-lived access token for the member
        llt=await m.cmd(type="auth/long_lived_access_token",client_name="ts-llt-probe",lifespan=365)
        llt_tok=llt["result"] if llt.get("success") else None
        log(f"  member long-lived token minted: {bool(llt_tok)}")

        # E7.8 CONTROL: long-lived token must work BEFORE removal
        if llt_tok:
            pc,pw_ = await conn(llt_tok)
            log(f"  CONTROL pre-removal long-lived token: {'ACCEPTED' if pc else 'rejected('+pw_.get('type','?')+')'}")
            if pc: await pc.ws.close()

        # --- CONTROL: member fires the event pre-removal ---
        await owner.cmd(type="call_service",domain="input_boolean",service="turn_off",target={"entity_id":EID})
        await asyncio.sleep(0.5)
        ev=await m.cmd(type="fire_event",event_type="ts_deputy_trigger")
        await asyncio.sleep(2)
        pre=await state(owner,EID)
        log(f"  CONTROL pre-removal: fire_event success={ev['success']} -> {EID}={pre}")

        # --- remove the member ---
        await owner.cmd(type="call_service",domain="input_boolean",service="turn_off",target={"entity_id":EID})
        await asyncio.sleep(0.5)
        d=await owner.cmd(type="config/auth/delete",user_id=uid)
        log(f"  DELETE user: success={d['success']}"); await asyncio.sleep(2)

        # --- E7.6 THE TEST: orphaned socket fires the event ---
        try:
            ev2=await m.cmd(type="fire_event",event_type="ts_deputy_trigger")
            await asyncio.sleep(2)
            post=await state(owner,EID)
            log(f"  >>> E7.6 POST-REMOVAL: fire_event success={ev2.get('success')} err={ev2.get('error')}")
            log(f"  >>> E7.6 {EID} = {post}   ==> DEPUTY RESIDUE: {post=='on'}")
        except Exception as e:
            log(f"  >>> E7.6 connection dead: {type(e).__name__}")

        # --- E7.8: does the long-lived token still authenticate a NEW connection? ---
        if llt_tok:
            nc,why=await conn(llt_tok)
            log(f"  >>> E7.8 long-lived token after REMOVAL: {'ACCEPTED' if nc else 'rejected('+why.get('type','?')+')'}")
            if nc: await nc.ws.close()
        try: await m.ws.close()
        except Exception: pass
        await owner.ws.close()

asyncio.run(main())
