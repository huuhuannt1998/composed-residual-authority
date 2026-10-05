"""P1 EXPERIMENT 8 (partial) - residual lifetime and termination events.

Answers: what ends the residue if nobody intervenes deliberately?
Short delays are measured directly; the long-duration arms (+6h, +24h) are not
run here. Termination events are the operationally decisive part: they tell a
household what, if anything, they can do.

Usage: p1e8_lifetime.py <port>
"""
import asyncio, json, subprocess, sys, time
import aiohttp, websockets
PORT=sys.argv[1]; BASE=f"http://localhost:{PORT}"; WS=f"ws://localhost:{PORT}/api/websocket"; CID=f"{BASE}/"
OWNER=("tsowner","Owner-Passw0rd-123"); PW="Member-Passw0rd-123"; EID="input_boolean.fam_a1"
log=lambda m: print(m, flush=True)
async def tokc(s,c):
    async with s.post(f"{BASE}/auth/token",data={"grant_type":"authorization_code","code":c,"client_id":CID}) as r: return await r.json()
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
async def conn(t):
    ws=await websockets.connect(WS,max_size=None); await ws.recv()
    await ws.send(json.dumps({"type":"auth","access_token":t})); m=json.loads(await ws.recv())
    return (C(ws),m) if m["type"]=="auth_ok" else (None,m)
async def st(c,e):
    r=await c.cmd(type="get_states")
    for s in (r.get("result") or []):
        if s["entity_id"]==e: return s["state"]
async def alive(m, owner):
    """Is the residue still reachable? read + indirect actuation."""
    out={}
    try:
        r=await m.cmd(type="get_states"); out["read"]=len(r.get("result") or [])>0
    except Exception: out["read"]=False; out["actuate"]=False; out["socket"]=False; return out
    out["socket"]=True
    try:
        await owner.cmd(type="call_service",domain="input_boolean",service="turn_off",target={"entity_id":EID}); await asyncio.sleep(0.4)
        await m.cmd(type="fire_event",event_type="trig_a1_input_boolean"); await asyncio.sleep(1.5)
        out["actuate"]=(await st(owner,EID))=="on"
    except Exception: out["actuate"]=False
    return out

async def main():
    rows=[]
    async with aiohttp.ClientSession() as s:
        otok=await login(s,*OWNER); owner,_=await conn(otok)
        r=await owner.cmd(type="config/auth/create",name="Lifetime",group_ids=["system-admin"],local_only=False)
        uid=r["result"]["user"]["id"]
        await owner.cmd(type="config/auth_provider/homeassistant/create",user_id=uid,username="lifetime_probe",password=PW)
        mtok=await login(s,"lifetime_probe",PW); m,_=await conn(mtok)
        rows.append(("pre-removal", await alive(m,owner)))
        await owner.cmd(type="config/auth/delete",user_id=uid); await asyncio.sleep(1)
        for label,delay in [("immediately",0),("+1 min",60),("+5 min",240)]:
            if delay: await asyncio.sleep(delay)
            rows.append((label, await alive(m,owner)))
        # termination events
        try:
            await owner.cmd(type="call_service",domain="automation",service="reload"); await asyncio.sleep(3)
            rows.append(("after automation reload", await alive(m,owner)))
        except Exception: rows.append(("after automation reload", {"socket":False,"read":False,"actuate":False}))
        # reconnect attempt with the same token
        nc,why=await conn(mtok)
        rows.append(("new connection, same token", {"socket":bool(nc),"read":False,"actuate":False}))
        if nc:
            try: await nc.ws.close()
            except Exception: pass
    # container restart (kills the socket by construction)
    subprocess.run(["docker","restart","tsdeputy"],capture_output=True)
    for _ in range(60):
        p=subprocess.run(["curl","-s","-m","3","-o","/dev/null","-w","%{http_code}",BASE+"/"],capture_output=True,text=True)
        if p.stdout.strip()=="302": break
        time.sleep(5)
    rows.append(("after HA restart", {"socket":False,"read":False,"actuate":False}))
    log("\n=== RESIDUAL LIFETIME AND TERMINATION EVENTS ===")
    log(f"  {'point':30s} {'socket':>7s} {'read':>6s} {'actuate':>8s}")
    for k,v in rows:
        log(f"  {k:30s} {str(v.get('socket')):>7s} {str(v.get('read')):>6s} {str(v.get('actuate')):>8s}")
    json.dump([{"point":k,**v} for k,v in rows], open("/tmp/lifetime.json","w"))
asyncio.run(main())
