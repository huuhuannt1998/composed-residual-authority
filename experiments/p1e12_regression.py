"""P1 EXPERIMENT 12 - lifecycle functional regression suite.

The ten-operation check was too small. This is the review's seven-group suite.
Every test declares its EXPECTED outcome, so failures are typed:

  functional regression : should have been ALLOWED, was DENIED  (defense broke a workflow)
  security   regression : should have been DENIED,  was ALLOWED (defense failed to close a path)

Run against any instance; pass the port. Compare the Defense A instance against
baseline to see that the defense closes security paths without breaking function.
"""
import asyncio, json, sys, time
import aiohttp, websockets
PORT=sys.argv[1] if len(sys.argv)>1 else "8142"
LABEL=sys.argv[2] if len(sys.argv)>2 else f"port {PORT}"
BASE=f"http://localhost:{PORT}"; WS=f"ws://localhost:{PORT}/api/websocket"; CID=f"{BASE}/"
OWNER=("tsowner","Owner-Passw0rd-123"); PW="Member-Passw0rd-123"; EID="input_boolean.ts_probe"
R=[]
def rec(group,name,expect,got,detail=""):
    kind="pass" if expect==got else ("security regression" if got=="allow" else "functional regression")
    R.append(dict(group=group,test=name,expect=expect,got=got,kind=kind,detail=detail))
    mark={"pass":"ok","security regression":"SEC-REG","functional regression":"FUNC-REG"}[kind]
    print(f"  [{mark:>7s}] {group:22s} {name:34s} expect={expect:6s} got={got}", flush=True)
async def tokc(s,c):
    async with s.post(f"{BASE}/auth/token",data={"grant_type":"authorization_code","code":c,"client_id":CID}) as r: return await r.json()
async def onboard(s):
    async with s.post(f"{BASE}/api/onboarding/users",json={"client_id":CID,"name":"TS Owner",
        "username":OWNER[0],"password":OWNER[1],"language":"en"}) as r:
        if r.status!=200: return None
        code=(await r.json())["auth_code"]
    t=(await tokc(s,code))["access_token"]
    for st in ("core_config","analytics"):
        async with s.post(f"{BASE}/api/onboarding/{st}",headers={"Authorization":f"Bearer {t}"}) as r: await r.text()
    return t
async def login(s,u,p):
    async with s.post(f"{BASE}/auth/login_flow",json={"client_id":CID,"handler":["homeassistant",None],"redirect_uri":CID,"type":"authorize"}) as r:
        f=(await r.json())["flow_id"]
    async with s.post(f"{BASE}/auth/login_flow/{f}",json={"client_id":CID,"username":u,"password":p}) as r:
        j=await r.json()
        if "result" not in j: return None
    return (await tokc(s,j["result"]))["access_token"]
class C:
    def __init__(s,ws): s.ws,s.id=ws,0
    async def cmd(s,**kw):
        s.id+=1; await s.ws.send(json.dumps({"id":s.id,**kw}))
        while True:
            m=json.loads(await asyncio.wait_for(s.ws.recv(),timeout=12))
            if m.get("id")==s.id and m["type"]=="result": return m
    async def drain(s,secs):
        out=[];end=asyncio.get_event_loop().time()+secs
        while asyncio.get_event_loop().time()<end:
            try: out.append(json.loads(await asyncio.wait_for(s.ws.recv(),timeout=max(0.1,end-asyncio.get_event_loop().time()))))
            except Exception: break
        return out
async def conn(t):
    try:
        ws=await websockets.connect(WS,max_size=None); await ws.recv()
        await ws.send(json.dumps({"type":"auth","access_token":t})); m=json.loads(await ws.recv())
        return (C(ws),m["type"]) if m["type"]=="auth_ok" else (None,m["type"])
    except Exception as e: return None,f"err:{type(e).__name__}"
async def ok(c,**kw):
    if c is None: return False
    try:
        r=await c.cmd(**kw); return bool(r.get("success"))
    except Exception: return False
async def st(c,e):
    try:
        r=await c.cmd(type="get_states")
        for x in (r.get("result") or []):
            if x["entity_id"]==e: return x["state"]
    except Exception: return None
A=lambda b: "allow" if b else "deny"
async def main():
    print(f"\n=== LIFECYCLE REGRESSION SUITE :: {LABEL} ===\n", flush=True)
    async with aiohttp.ClientSession() as s:
        otok=await onboard(s) or await login(s,*OWNER)
        owner,_=await conn(otok)
        try: await owner.cmd(type="input_boolean/create",name="ts probe")
        except Exception: pass
        await asyncio.sleep(1.2)
        H={"Authorization":f"Bearer {otok}","Content-Type":"application/json"}
        async with s.post(f"{BASE}/api/config/automation/config/tsreg",headers=H,
            json={"alias":"ts regression automation","trigger":[{"platform":"event","event_type":"ts_reg_trigger"}],
                  "action":[{"service":"input_boolean.turn_on","target":{"entity_id":EID}}],"mode":"single"}) as r: await r.text()
        await owner.cmd(type="call_service",domain="automation",service="reload"); await asyncio.sleep(2)

        # ---------- 1. onboarding -------------------------------------------
        g="1 onboarding"
        r=await owner.cmd(type="config/auth/create",name="reg member",group_ids=["system-users"],local_only=False)
        muid=r["result"]["user"]["id"]; rec(g,"create user","allow",A(bool(muid)))
        rec(g,"activate user","allow",A(bool(r["result"]["user"].get("is_active",True))))
        await owner.cmd(type="config/auth_provider/homeassistant/create",user_id=muid,username="regmember",password=PW)
        mtok=await login(s,"regmember",PW); rec(g,"authenticate","allow",A(bool(mtok)))
        mem,_=await conn(mtok); rec(g,"establish session","allow",A(mem is not None))

        # ---------- 2. normal member ----------------------------------------
        g="2 normal member"
        rec(g,"state read","allow",A(await ok(mem,type="get_states")))
        sub=await ok(mem,type="subscribe_events",event_type="state_changed")
        await owner.cmd(type="call_service",domain="input_boolean",service="toggle",target={"entity_id":EID})
        got=sub and any(e.get("type")=="event" for e in await mem.drain(1.6))
        rec(g,"state subscription","allow",A(got))
        rec(g,"direct device operation","allow",
            A(await ok(mem,type="call_service",domain="input_boolean",service="turn_on",target={"entity_id":EID})))
        rec(g,"script exec (admin-gated)","deny",
            A(await ok(mem,type="execute_script",sequence=[{"service":"input_boolean.turn_on","target":{"entity_id":EID}}])))

        # ---------- 3. normal administrator ---------------------------------
        g="3 normal admin"
        r=await owner.cmd(type="config/auth/create",name="reg admin",group_ids=["system-admin"],local_only=False)
        auid=r["result"]["user"]["id"]
        await owner.cmd(type="config/auth_provider/homeassistant/create",user_id=auid,username="regadmin",password=PW)
        atok=await login(s,"regadmin",PW); adm,_=await conn(atok)
        rec(g,"list users","allow",A(await ok(adm,type="config/auth/list")))
        rec(g,"fire events","allow",A(await ok(adm,type="fire_event",event_type="ts_reg_ping")))
        rec(g,"modify configuration","allow",A(await ok(adm,type="input_boolean/create",name="admin made")))

        # ---------- 4. deactivation -----------------------------------------
        g="4 deactivation"
        await owner.cmd(type="config/auth/update",user_id=muid,is_active=False); await asyncio.sleep(1.5)
        rec(g,"session closes","deny",A(await ok(mem,type="get_states")))
        m2,why=await conn(mtok); rec(g,"reconnect denied","deny",A(m2 is not None),why)
        if m2:
            try: await m2.ws.close()
            except Exception: pass

        # ---------- 5. deletion ---------------------------------------------
        g="5 deletion"
        await owner.cmd(type="config/auth/delete",user_id=auid); await asyncio.sleep(1.5)
        rec(g,"session closes / ops denied","deny",A(await ok(adm,type="get_states")))
        rec(g,"indirect actuation denied","deny",A(await ok(adm,type="fire_event",event_type="ts_reg_trigger")))
        a2,why=await conn(atok); rec(g,"reconnect denied","deny",A(a2 is not None),why)
        if a2:
            try: await a2.ws.close()
            except Exception: pass

        # ---------- 6. post-removal owner operation --------------------------
        g="6 owner after removal"
        rec(g,"owner state read","allow",A(await ok(owner,type="get_states")))
        rec(g,"owner service call","allow",
            A(await ok(owner,type="call_service",domain="input_boolean",service="turn_off",target={"entity_id":EID})))
        rec(g,"owner list users","allow",A(await ok(owner,type="config/auth/list")))
        rec(g,"owner create user","allow",A(await ok(owner,type="config/auth/create",name="post rm",group_ids=["system-users"],local_only=False)))

        # ---------- 7. automation behaviour ----------------------------------
        g="7 automation"
        await owner.cmd(type="call_service",domain="input_boolean",service="turn_off",target={"entity_id":EID}); await asyncio.sleep(0.5)
        await owner.cmd(type="fire_event",event_type="ts_reg_trigger"); await asyncio.sleep(1.6)
        rec(g,"legitimate automation triggers","allow",A((await st(owner,EID))=="on"))
        r=await owner.cmd(type="config/auth/create",name="cur admin",group_ids=["system-admin"],local_only=False)
        cuid=r["result"]["user"]["id"]
        await owner.cmd(type="config/auth_provider/homeassistant/create",user_id=cuid,username="curadmin",password=PW)
        ctok=await login(s,"curadmin",PW); cur,_=await conn(ctok)
        await owner.cmd(type="call_service",domain="input_boolean",service="turn_off",target={"entity_id":EID}); await asyncio.sleep(0.5)
        await ok(cur,type="fire_event",event_type="ts_reg_trigger"); await asyncio.sleep(1.6)
        rec(g,"authorized principal trigger path","allow",A((await st(owner,EID))=="on"))

        # ---------- summary ---------------------------------------------------
        npass=sum(1 for x in R if x["kind"]=="pass")
        sec=[x for x in R if x["kind"]=="security regression"]
        fun=[x for x in R if x["kind"]=="functional regression"]
        print(f"\n  {len(R)} tests")
        print(f"  {npass} passed")
        print(f"  {len(sec)} security regressions")
        print(f"  {len(fun)} functional regressions")
        for x in sec+fun: print(f"    -> {x['kind']}: {x['group']} / {x['test']} (expected {x['expect']}, got {x['got']}) {x['detail']}")
        json.dump({"label":LABEL,"tests":R,"passed":npass,"security_regressions":len(sec),
                   "functional_regressions":len(fun)},open(f"/tmp/p1e12_{PORT}.json","w"),indent=1)
asyncio.run(main())
