"""C5 / E6.7 - does TSMON deny any LEGITIMATE operation?

Closure alone is half an evaluation. A monitor that denies too much is useless.
This runs the five legitimate workflows against the instance and records, for a
CURRENT (non-removed) principal, whether every operation still succeeds.
Run once with TSMON applied and once reverted; results must be identical.
"""
import asyncio, json, sys, time
import aiohttp, websockets
BASE="http://localhost:8124"; WS="ws://localhost:8124/api/websocket"; CID="http://localhost:8124/"
OWNER=("tsowner","Owner-Passw0rd-123"); PW="Member-Passw0rd-123"; EID="input_boolean.ts_probe"
TAG=sys.argv[1] if len(sys.argv)>1 else "run"
log=lambda m: print(m, flush=True)
async def tokc(s,c):
    async with s.post(f"{BASE}/auth/token",data={"grant_type":"authorization_code","code":c,"client_id":CID}) as r: return await r.json()
async def login(s,u,p):
    async with s.post(f"{BASE}/auth/login_flow",json={"client_id":CID,"handler":["homeassistant",None],"redirect_uri":CID,"type":"authorize"}) as r: f=(await r.json())["flow_id"]
    async with s.post(f"{BASE}/auth/login_flow/{f}",json={"client_id":CID,"username":u,"password":p}) as r:
        j=await r.json()
        if "result" not in j: raise SystemExit(f"login {u}: {j}")
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
    for s in (r.get("result") or []):
        if s["entity_id"]==e: return s["state"]

async def main():
    res={}
    async with aiohttp.ClientSession() as s:
        otok=await login(s,*OWNER); owner,_=await conn(otok)
        u=f"legit_{TAG}"
        # W1 onboard a member
        r=await owner.cmd(type="config/auth/create",name=f"Legit {TAG}",group_ids=["system-admin"],local_only=False)
        uid=r["result"]["user"]["id"]
        await owner.cmd(type="config/auth_provider/homeassistant/create",user_id=uid,username=u,password=PW)
        res["W1_onboard_member"]=bool(r.get("success"))
        # member authenticates
        mtok=await login(s,u,PW); m,why=await conn(mtok)
        res["W2_member_authenticates"]=m is not None
        # W3 current member reads state
        g=await m.cmd(type="get_states")
        res["W3_current_member_reads"]=bool(g.get("success")) and len(g.get("result") or [])>0
        # W4 current member actuates via service call
        await owner.cmd(type="call_service",domain="input_boolean",service="turn_off",target={"entity_id":EID}); await asyncio.sleep(0.4)
        a=await m.cmd(type="call_service",domain="input_boolean",service="turn_on",target={"entity_id":EID}); await asyncio.sleep(1)
        res["W4_current_member_actuates"]=bool(a.get("success")) and (await state(owner,EID))=="on"
        # W5 current admin uses admin-gated commands (the paths TSMON patches)
        e=await m.cmd(type="fire_event",event_type="ts_legit_probe")
        l=await m.cmd(type="config/auth/list")
        res["W5_current_admin_fire_event"]=bool(e.get("success"))
        res["W5_current_admin_config_list"]=bool(l.get("success"))
        # W6 subscriptions
        sub=await m.cmd(type="subscribe_events",event_type="state_changed")
        res["W6_current_member_subscribes"]=bool(sub.get("success"))
        # W7 owner deactivates then removes (lifecycle completes cleanly)
        d=await owner.cmd(type="config/auth/update",user_id=uid,is_active=False)
        res["W7_deactivate_succeeds"]=bool(d.get("success")); await asyncio.sleep(1)
        rm=await owner.cmd(type="config/auth/delete",user_id=uid)
        res["W8_remove_succeeds"]=bool(rm.get("success"))
        # W9 owner (never removed) still fully functional afterwards
        o1=await owner.cmd(type="get_states"); o2=await owner.cmd(type="fire_event",event_type="ts_owner_probe")
        res["W9_owner_unaffected"]=bool(o1.get("success")) and bool(o2.get("success"))
        try: await m.ws.close()
        except Exception: pass
        await owner.ws.close()
    ok=sum(1 for v in res.values() if v); tot=len(res)
    log(f"\n=== LEGITIMATE WORKFLOWS [{TAG}] ===")
    for k,v in res.items(): log(f"  {'PASS' if v else 'FAIL'}  {k}")
    log(f"\n  {ok}/{tot} legitimate operations succeeded")
    json.dump(res, open(f"/tmp/fp_{TAG}.json","w"))
asyncio.run(main())
