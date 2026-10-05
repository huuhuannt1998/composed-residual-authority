"""P1 EXPERIMENT 7b - SESSION CONDITIONS and the remaining transitions.

The main matrix (p1e7_matrix.py) varies role x transition x operation on a single
pre-existing socket. This file varies the SESSION CONDITION and covers the two
transitions the matrix does not: explicit refresh-token revocation, and the
attempt to open a NEW connection after the transition.

Arms:
  A1 two_sockets     two concurrent sockets for one principal, then delete
  A2 new_conn_delete after delete, authenticate a FRESH socket with the old token
  A3 longlived       long-lived access token, then delete
  A4 token_revoke    revoke the refresh token instead of deleting the user
  A5 new_conn_deact  after deactivate, authenticate a fresh socket
"""
import asyncio, json, sys
import aiohttp, websockets
PORT=sys.argv[1] if len(sys.argv)>1 else "8137"
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
    for st in ("core_config","analytics"):
        async with s.post(f"{BASE}/api/onboarding/{st}",headers={"Authorization":f"Bearer {t}"}) as r: await r.text()
    return t
async def login(s,u,p):
    async with s.post(f"{BASE}/auth/login_flow",json={"client_id":CID,"handler":["homeassistant",None],"redirect_uri":CID,"type":"authorize"}) as r: f=(await r.json())["flow_id"]
    async with s.post(f"{BASE}/auth/login_flow/{f}",json={"client_id":CID,"username":u,"password":p}) as r:
        j=await r.json()
        if "result" not in j: return None,None
    d=await tokc(s,j["result"]); return d["access_token"], d.get("refresh_token")
class C:
    def __init__(s,ws): s.ws,s.id=ws,0
    async def cmd(s,**kw):
        s.id+=1; await s.ws.send(json.dumps({"id":s.id,**kw}))
        while True:
            m=json.loads(await asyncio.wait_for(s.ws.recv(),timeout=12))
            if m.get("id")==s.id and m["type"]=="result": return m
async def conn(t):
    try:
        ws=await websockets.connect(WS,max_size=None); await ws.recv()
        await ws.send(json.dumps({"type":"auth","access_token":t})); m=json.loads(await ws.recv())
        return (C(ws),m["type"]) if m["type"]=="auth_ok" else (None,m["type"])
    except Exception as e: return None, f"conn_error:{type(e).__name__}"
async def st(c,e):
    r=await c.cmd(type="get_states")
    for s in (r.get("result") or []):
        if s["entity_id"]==e: return s["state"]
async def probe(m, owner):
    """(socket_alive, read, actuate_via_deputy)"""
    if m is None: return dict(socket=False,read=False,actuate=False)
    try:
        r=await m.cmd(type="get_states"); read=len(r.get("result") or [])>0
    except Exception: return dict(socket=False,read=False,actuate=False)
    await owner.cmd(type="call_service",domain="input_boolean",service="turn_off",target={"entity_id":EID}); await asyncio.sleep(0.3)
    try: await m.cmd(type="fire_event",event_type="ts_deputy_trigger")
    except Exception: pass
    await asyncio.sleep(1.4)
    return dict(socket=True,read=read,actuate=(await st(owner,EID))=="on")
async def mkuser(s,owner,u,gid="system-admin"):
    r=await owner.cmd(type="config/auth/create",name=u,group_ids=[gid],local_only=False)
    uid=r["result"]["user"]["id"]
    await owner.cmd(type="config/auth_provider/homeassistant/create",user_id=uid,username=u,password=PW)
    at,rt=await login(s,u,PW); return uid,at,rt
async def main():
    async with aiohttp.ClientSession() as s:
        otok=await onboard(s) or (await login(s,*OWNER))[0]
        owner,_=await conn(otok)
        try: await owner.cmd(type="input_boolean/create",name="ts probe")
        except Exception: pass
        await asyncio.sleep(1.2)
        H={"Authorization":f"Bearer {otok}","Content-Type":"application/json"}
        async with s.post(f"{BASE}/api/config/automation/config/tsdeputy",headers=H,
            json={"alias":"ts deputy probe","trigger":[{"platform":"event","event_type":"ts_deputy_trigger"}],
                  "action":[{"service":"input_boolean.turn_on","target":{"entity_id":EID}}],"mode":"single"}) as r: await r.text()
        await owner.cmd(type="call_service",domain="automation",service="reload"); await asyncio.sleep(2)
        R=[]
        # ---- A1: two concurrent sockets, then delete -------------------------
        uid,at,rt=await mkuser(s,owner,"sess_two")
        mA,_=await conn(at); mB,_=await conn(at)
        pA,pB=await probe(mA,owner), await probe(mB,owner)
        await owner.cmd(type="config/auth/delete",user_id=uid); await asyncio.sleep(1.5)
        R.append(("A1 two sockets / socket #1","pre",pA,"post",await probe(mA,owner)))
        R.append(("A1 two sockets / socket #2","pre",pB,"post",await probe(mB,owner)))
        for x in (mA,mB):
            try: await x.ws.close()
            except Exception: pass
        # ---- A2: NEW connection with the old token after delete --------------
        uid,at,rt=await mkuser(s,owner,"sess_newc")
        m,_=await conn(at); pre=await probe(m,owner)
        await owner.cmd(type="config/auth/delete",user_id=uid); await asyncio.sleep(1.5)
        try: await m.ws.close()
        except Exception: pass
        m2,why=await conn(at)
        R.append((f"A2 fresh socket after delete [{why}]","pre",pre,"post",await probe(m2,owner)))
        # ---- A3: long-lived access token, then delete ------------------------
        uid,at,rt=await mkuser(s,owner,"sess_llat")
        m,_=await conn(at)
        try:
            r=await m.cmd(type="auth/long_lived_access_token",client_name="ts-llat",lifespan=10)
            llat=r.get("result")
        except Exception: llat=None
        pre=await probe(m,owner)
        await owner.cmd(type="config/auth/delete",user_id=uid); await asyncio.sleep(1.5)
        R.append(("A3 long-lived tok / original socket","pre",pre,"post",await probe(m,owner)))
        if llat:
            m3,why=await conn(llat)
            R.append((f"A3 long-lived tok / fresh socket [{why}]","pre",dict(socket=True,read=True,actuate=True),"post",await probe(m3,owner)))
        else: R.append(("A3 long-lived tok / fresh socket [NOT ISSUED]","pre",{},"post",{}))
        try: await m.ws.close()
        except Exception: pass
        # ---- A4: explicit refresh-token revocation (user NOT deleted) --------
        uid,at,rt=await mkuser(s,owner,"sess_revk")
        m,_=await conn(at); pre=await probe(m,owner)
        rr=await owner.cmd(type="config/auth/list")   # locate the principal's refresh tokens
        killed=False
        try:
            r=await m.cmd(type="auth/refresh_tokens")
            for t in (r.get("result") or []):
                if t.get("type")=="normal":
                    await m.cmd(type="auth/delete_refresh_token",refresh_token_id=t["id"]); killed=True
        except Exception as e: killed=f"err:{e}"
        await asyncio.sleep(1.5)
        R.append((f"A4 refresh-token revoked (killed={killed})","pre",pre,"post",await probe(m,owner)))
        await owner.cmd(type="config/auth/delete",user_id=uid)
        # ---- A5: fresh connection after DEACTIVATE ---------------------------
        uid,at,rt=await mkuser(s,owner,"sess_deact")
        m,_=await conn(at); pre=await probe(m,owner)
        await owner.cmd(type="config/auth/update",user_id=uid,is_active=False); await asyncio.sleep(1.5)
        post_old=await probe(m,owner)
        try: await m.ws.close()
        except Exception: pass
        m5,why=await conn(at)
        R.append(("A5 deactivate / original socket","pre",pre,"post",post_old))
        R.append((f"A5 deactivate / fresh socket [{why}]","pre",pre,"post",await probe(m5,owner)))
        await owner.cmd(type="config/auth/delete",user_id=uid)
        log("\n=== SESSION-CONDITION ARMS (role=admin, deputy present) ===")
        log(f"  {'arm':46s} {'pre s/r/a':>12s}   {'post s/r/a':>12s}")
        f=lambda d: f"{int(d.get('socket',0))}/{int(d.get('read',0))}/{int(d.get('actuate',0))}" if d else "  -/-/-"
        for name,_,pre,_,post in R: log(f"  {name:46s} {f(pre):>12s}   {f(post):>12s}")
        json.dump([(n,p,q) for n,_,p,_,q in R], open("/tmp/p1e7b.json","w"))
asyncio.run(main())
