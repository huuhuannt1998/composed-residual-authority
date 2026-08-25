"""P1 EXPERIMENT 6 - Home Assistant multi-version study.

Runs the post-removal capability probes against a freshly onboarded instance of
a given version, to establish whether the deletion/session asymmetry is
release-specific or structural. Takes the base URL of an already-running
instance so container lifecycle stays in the shell.

Usage: p1e6_version_study.py <port> <version-label>
"""
import asyncio, json, sys
import aiohttp, websockets
PORT=sys.argv[1]; VER=sys.argv[2]
BASE=f"http://localhost:{PORT}"; WS=f"ws://localhost:{PORT}/api/websocket"; CID=f"{BASE}/"
OWNER=("tsowner","Owner-Passw0rd-123"); PW="Member-Passw0rd-123"; EID="input_boolean.ts_probe"
log=lambda m: print(m, flush=True)

async def tokc(s,c):
    async with s.post(f"{BASE}/auth/token",data={"grant_type":"authorization_code","code":c,"client_id":CID}) as r: return await r.json()
async def onboard(s):
    async with s.post(f"{BASE}/api/onboarding/users",json={"client_id":CID,"name":"TS Owner",
        "username":OWNER[0],"password":OWNER[1],"language":"en"}) as r:
        if r.status!=200: return None
        code=(await r.json())["auth_code"]
    t=(await tokc(s,code))["access_token"]
    for step in ("core_config","analytics"):
        async with s.post(f"{BASE}/api/onboarding/{step}",headers={"Authorization":f"Bearer {t}"}) as r: await r.text()
    return t
async def login(s,u,p):
    async with s.post(f"{BASE}/auth/login_flow",json={"client_id":CID,"handler":["homeassistant",None],"redirect_uri":CID,"type":"authorize"}) as r: f=(await r.json())["flow_id"]
    async with s.post(f"{BASE}/auth/login_flow/{f}",json={"client_id":CID,"username":u,"password":p}) as r:
        j=await r.json()
        if "result" not in j: return None
    return (await tokc(s,j["result"]))["access_token"]
class C:
    def __init__(s,ws): s.ws,s.id=ws,0
    async def cmd(s,**kw):
        s.id+=1; await s.ws.send(json.dumps({"id":s.id,**kw}))
        while True:
            m=json.loads(await asyncio.wait_for(s.ws.recv(),timeout=15))
            if m.get("id")==s.id and m["type"]=="result": return m
    async def drain(s,secs):
        out=[];end=asyncio.get_event_loop().time()+secs
        while asyncio.get_event_loop().time()<end:
            try: out.append(json.loads(await asyncio.wait_for(s.ws.recv(),timeout=max(0.1,end-asyncio.get_event_loop().time()))))
            except Exception: break
        return out
async def conn(t):
    ws=await websockets.connect(WS,max_size=None); await ws.recv()
    await ws.send(json.dumps({"type":"auth","access_token":t})); m=json.loads(await ws.recv())
    return (C(ws),m) if m["type"]=="auth_ok" else (None,m)
async def state(c,e):
    r=await c.cmd(type="get_states")
    for s in (r.get("result") or []):
        if s["entity_id"]==e: return s["state"]

async def probe(m,owner):
    o={}
    async def ok(k,coro):
        try: r=await coro; o[k]=bool(r.get("success"))
        except Exception: o[k]=False
    try:
        r=await m.cmd(type="get_states"); o["read"]=len(r.get("result") or [])>0
    except Exception: o["read"]=False
    await ok("user_enum", m.cmd(type="config/auth/list"))
    await ok("service_call", m.cmd(type="call_service",domain="input_boolean",service="turn_on",target={"entity_id":EID}))
    await ok("event_fire", m.cmd(type="fire_event",event_type="ts_ver_probe"))
    try:
        r=await m.cmd(type="subscribe_events",event_type="state_changed"); reg=bool(r.get("success"))
    except Exception: reg=False
    await owner.cmd(type="call_service",domain="input_boolean",service="toggle",target={"entity_id":EID})
    ev=await m.drain(2.5)
    o["new_stream"]=reg and any(e.get("type")=="event" for e in ev)
    await owner.cmd(type="call_service",domain="input_boolean",service="turn_off",target={"entity_id":EID}); await asyncio.sleep(0.5)
    try: await m.cmd(type="fire_event",event_type="ts_deputy_trigger")
    except Exception: pass
    await asyncio.sleep(2)
    o["indirect_actuation"]=(await state(owner,EID))=="on"
    return o

async def main():
    res={"version":VER}
    async with aiohttp.ClientSession() as s:
        otok=await onboard(s)
        if not otok: otok=await login(s,*OWNER)
        if not otok: log(f"{VER}: ONBOARD/LOGIN FAILED"); return
        owner,_=await conn(otok)
        try: await owner.cmd(type="input_boolean/create",name="ts probe")
        except Exception: pass
        await asyncio.sleep(1.5)
        auto={"alias":"ts deputy probe","trigger":[{"platform":"event","event_type":"ts_deputy_trigger"}],
              "action":[{"service":"input_boolean.turn_on","target":{"entity_id":EID}}],"mode":"single"}
        async with s.post(f"{BASE}/api/config/automation/config/tsdeputy",
            headers={"Authorization":f"Bearer {otok}","Content-Type":"application/json"},json=auto) as r: await r.text()
        try: await owner.cmd(type="call_service",domain="automation",service="reload")
        except Exception: pass
        await asyncio.sleep(2)
        try: await owner.cmd(type="call_service",domain="automation",service="turn_on",target={"entity_id":"automation.ts_deputy_probe"})
        except Exception: pass
        r=await owner.cmd(type="config/auth/create",name="Ver Probe",group_ids=["system-admin"],local_only=False)
        uid=r["result"]["user"]["id"]
        await owner.cmd(type="config/auth_provider/homeassistant/create",user_id=uid,username="ver_probe",password=PW)
        mtok=await login(s,"ver_probe",PW); m,_=await conn(mtok)
        res["pre"]=await probe(m,owner)
        await owner.cmd(type="config/auth/delete",user_id=uid); await asyncio.sleep(2)
        try:
            res["post"]=await probe(m,owner); res["socket_survives"]=True
        except Exception as e:
            res["post"]={k:False for k in res["pre"]}; res["socket_survives"]=False
        log(f"\n=== {VER} ===")
        log(f"  socket survives delete : {res['socket_survives']}")
        for k in res["pre"]:
            log(f"  {k:20s} pre={str(res['pre'][k]):5s} post={str(res['post'].get(k)):5s}"
                + ("   RESIDUAL" if res['pre'][k] and res['post'].get(k) else ""))
        json.dump(res, open(f"/tmp/ver_{VER}.json","w"))
asyncio.run(main())
