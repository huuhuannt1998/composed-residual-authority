"""E3.4/E3.5 — counterfactual necessity + matched-budget control for the HA deputy residue.
Witness W = { orphaned socket, event-triggered household automation }.
Each arm removes ONE witness element; the residue must COLLAPSE in every arm."""
import asyncio, json
import aiohttp, websockets
BASE="http://localhost:8124"; WS="ws://localhost:8124/api/websocket"; CID="http://localhost:8124/"
OWNER=("tsowner","Owner-Passw0rd-123"); PW="Member-Passw0rd-123"; EID="input_boolean.ts_probe"
log=lambda m: print(m, flush=True)
async def tokc(s,c):
    async with s.post(f"{BASE}/auth/token",data={"grant_type":"authorization_code","code":c,"client_id":CID}) as r: return await r.json()
async def onboard(s):
    """The runner supplies a FRESH instance, so create the owner rather than
    assuming one exists. Logging in blind against a clean container fails with
    invalid_auth, which reads as an auth defect rather than missing setup."""
    async with s.post(f"{BASE}/api/onboarding/users",json={"client_id":CID,"name":"TS Owner",
        "username":OWNER[0],"password":OWNER[1],"language":"en"}) as r:
        if r.status!=200: return None
        code=(await r.json())["auth_code"]
    t=(await tokc(s,code))["access_token"]
    for st in ("core_config","analytics"):
        async with s.post(f"{BASE}/api/onboarding/{st}",headers={"Authorization":f"Bearer {t}"}) as r:
            await r.text()
    return t

async def login(s,u,p):
    async with s.post(f"{BASE}/auth/login_flow",json={"client_id":CID,"handler":["homeassistant",None],"redirect_uri":CID,"type":"authorize"}) as r: f=(await r.json())["flow_id"]
    async with s.post(f"{BASE}/auth/login_flow/{f}",json={"client_id":CID,"username":u,"password":p}) as r:
        j=await r.json()
        if "result" not in j: raise SystemExit(j)
    return (await tokc(s,j["result"]))["access_token"]
class C:
    def __init__(s,ws): s.ws,s.id=ws,0
    async def cmd(s,**kw):
        s.id+=1; await s.ws.send(json.dumps({"id":s.id,**kw}))
        while True:
            m=json.loads(await asyncio.wait_for(s.ws.recv(),timeout=15))
            if m.get("id")==s.id and m["type"]=="result": return m
async def conn(t):
    ws=await websockets.connect(WS,max_size=None); await ws.recv()
    await ws.send(json.dumps({"type":"auth","access_token":t})); m=json.loads(await ws.recv())
    return (C(ws),m) if m["type"]=="auth_ok" else (None,m)
async def state(c,e):
    r=await c.cmd(type="get_states")
    for s in r["result"]:
        if s["entity_id"]==e: return s["state"]

async def setup_auto(s,otok,owner,enabled=True):
    auto={"alias":"ts deputy probe","trigger":[{"platform":"event","event_type":"ts_deputy_trigger"}],
          "action":[{"service":"input_boolean.turn_on","target":{"entity_id":EID}}],"mode":"single"}
    async with s.post(f"{BASE}/api/config/automation/config/tsdeputy",
        headers={"Authorization":f"Bearer {otok}","Content-Type":"application/json"},json=auto) as r: await r.text()
    await owner.cmd(type="call_service",domain="automation",service="reload"); await asyncio.sleep(2)
    if not enabled:
        await owner.cmd(type="call_service",domain="automation",service="turn_off",
                        target={"entity_id":"automation.ts_deputy_probe"}); await asyncio.sleep(1)

async def arm(s,otok,owner,label,keep_socket,keep_auto,n):
    await setup_auto(s,otok,owner,enabled=keep_auto)
    r=await owner.cmd(type="config/auth/create",name=f"TSN{n}",group_ids=["system-admin"],local_only=False)
    uid=r["result"]["user"]["id"]; un=f"member_n{n}"
    await owner.cmd(type="config/auth_provider/homeassistant/create",user_id=uid,username=un,password=PW)
    mtok=await login(s,un,PW); m,_=await conn(mtok)
    await owner.cmd(type="call_service",domain="input_boolean",service="turn_off",target={"entity_id":EID}); await asyncio.sleep(0.5)
    await owner.cmd(type="config/auth/delete",user_id=uid); await asyncio.sleep(2)
    if not keep_socket:
        try: await m.ws.close()
        except Exception: pass
        await asyncio.sleep(1)
    fired=None
    try:
        r2=await m.cmd(type="fire_event",event_type="ts_deputy_trigger"); fired=r2.get("success")
    except Exception as e: fired=f"socket dead ({type(e).__name__})"
    await asyncio.sleep(2)
    st=await state(owner,EID)
    residue = (st=="on")
    log(f"  {label:44s} fire={str(fired):8s} entity={str(st):4s}  RESIDUE={residue}")
    try: await m.ws.close()
    except Exception: pass
    return residue

async def main():
    async with aiohttp.ClientSession() as s:
        otok=await onboard(s) or await login(s,*OWNER); owner,_=await conn(otok)
        # Written against an instance where an earlier experiment had already
        # created the probe entity. On a fresh container it does not exist, so
        # actuation cannot be observed and the result reads as "no residue"
        # rather than "no measurement".
        try: await owner.cmd(type="input_boolean/create",name="ts probe")
        except Exception: pass
        await asyncio.sleep(1.2)
        log("E3.4 COUNTERFACTUAL NECESSITY — each arm removes ONE witness element\n")
        full = await arm(s,otok,owner,"FULL witness (socket + automation)",   True,  True,  10)
        noSock = await arm(s,otok,owner,"minus orphaned socket",              False, True,  11)
        noAuto = await arm(s,otok,owner,"minus automation (disabled)",        True,  False, 12)
        log("")
        collapsed = (not noSock) and (not noAuto)
        log(f"  full residue present : {full}")
        log(f"  collapses without socket    : {not noSock}")
        log(f"  collapses without automation: {not noAuto}")
        log(f"\n  >>> A5 NECESSITY: {'PASS' if (full and collapsed) else 'FAIL'}   CRD = 2 confirmed: {full and collapsed}")
        await owner.ws.close()
asyncio.run(main())
