"""P1 EXPERIMENT 7 - role x transition x operation matrix with repetitions.

Turns one vulnerability trace into a systematic evaluation. Each independent run
creates a fresh principal, authenticates a WebSocket, records the pre-transition
capability vector, applies the transition, and records the post vector on the
SAME socket. Proportions are reported with Wilson 95% intervals.

Usage: p1e7_matrix.py <port> <reps>
"""
import asyncio, json, sys
import aiohttp, websockets
PORT=sys.argv[1]; REPS=int(sys.argv[2]) if len(sys.argv)>2 else 30
BASE=f"http://localhost:{PORT}"; WS=f"ws://localhost:{PORT}/api/websocket"; CID=f"{BASE}/"
OWNER=("tsowner","Owner-Passw0rd-123"); PW="Member-Passw0rd-123"; EID="input_boolean.ts_probe"
log=lambda m: print(m, flush=True)
OPS=["read","new_subscribe","existing_stream","user_enum","direct_actuate",
     "script_exec","event_fire","indirect_actuate"]

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
    ws=await websockets.connect(WS,max_size=None); await ws.recv()
    await ws.send(json.dumps({"type":"auth","access_token":t})); m=json.loads(await ws.recv())
    return (C(ws),m) if m["type"]=="auth_ok" else (None,m)
async def st(c,e):
    r=await c.cmd(type="get_states")
    for s in (r.get("result") or []):
        if s["entity_id"]==e: return s["state"]

async def vector(m, owner, phase):
    """phase='pre' registers the durable subscription; phase='post' tests both
    the pre-registered stream and a freshly registered one, which are distinct
    operations and are measured on distinct event types."""
    v={k:False for k in OPS}
    try:
        r=await m.cmd(type="get_states"); v["read"]=len(r.get("result") or [])>0
    except Exception: return v          # socket dead: every operation unavailable
    for k,c in [("user_enum",dict(type="config/auth/list")),
                ("direct_actuate",dict(type="call_service",domain="input_boolean",service="turn_on",target={"entity_id":EID})),
                ("script_exec",dict(type="execute_script",sequence=[{"service":"input_boolean.turn_on","target":{"entity_id":EID}}])),
                ("event_fire",dict(type="fire_event",event_type="mx_ping"))]:
        try: r=await m.cmd(**c); v[k]=bool(r.get("success"))
        except Exception: v[k]=False
    if phase=="pre":
        try: r=await m.cmd(type="subscribe_events",event_type="state_changed"); reg=bool(r.get("success"))
        except Exception: reg=False
        await owner.cmd(type="call_service",domain="input_boolean",service="toggle",target={"entity_id":EID})
        ev=await m.drain(1.6)
        v["existing_stream"]=reg and any(e.get("type")=="event" for e in ev)
        v["new_subscribe"]=v["existing_stream"]     # same act pre-transition
    else:
        # (a) does the subscription registered BEFORE the transition still deliver?
        await owner.cmd(type="call_service",domain="input_boolean",service="toggle",target={"entity_id":EID})
        ev=await m.drain(1.6)
        v["existing_stream"]=any(e.get("type")=="event" for e in ev)
        # (b) can a NEW subscription be registered and delivered on, post-transition?
        try: r=await m.cmd(type="subscribe_events",event_type="mx_fresh"); reg=bool(r.get("success"))
        except Exception: reg=False
        try: await owner.cmd(type="fire_event",event_type="mx_fresh")
        except Exception: pass
        ev2=await m.drain(1.6)
        v["new_subscribe"]=reg and any(e.get("type")=="event" and e.get("event",{}).get("event_type")=="mx_fresh" for e in ev2)
    await owner.cmd(type="call_service",domain="input_boolean",service="turn_off",target={"entity_id":EID}); await asyncio.sleep(0.3)
    try: await m.cmd(type="fire_event",event_type="ts_deputy_trigger")
    except Exception: pass
    await asyncio.sleep(1.4)
    v["indirect_actuate"]=(await st(owner,EID))=="on"
    return v

def wilson(k,n,z=1.96):
    if n==0: return (0.0,0.0)
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d; s=z*((p*(1-p)/n+z*z/(4*n*n))**0.5)/d
    return max(0.0,c-s), min(1.0,c+s)

async def main():
    async with aiohttp.ClientSession() as s:
        otok=await onboard(s) or await login(s,*OWNER)
        owner,_=await conn(otok)
        try: await owner.cmd(type="input_boolean/create",name="ts probe")
        except Exception: pass
        await asyncio.sleep(1.2)
        H={"Authorization":f"Bearer {otok}","Content-Type":"application/json"}
        async with s.post(f"{BASE}/api/config/automation/config/tsdeputy",headers=H,
            json={"alias":"ts deputy probe","trigger":[{"platform":"event","event_type":"ts_deputy_trigger"}],
                  "action":[{"service":"input_boolean.turn_on","target":{"entity_id":EID}}],"mode":"single"}) as r: await r.text()
        try: await owner.cmd(type="call_service",domain="automation",service="reload")
        except Exception: pass
        await asyncio.sleep(2)
        results={}
        for role,gid in [("user","system-users"),("admin","system-admin")]:
            for trans in ["delete","deactivate"]:
                arm=f"{role}/{trans}"; counts={k:0 for k in OPS}; pre_counts={k:0 for k in OPS}; n=0
                for i in range(REPS):
                    u=f"mx_{role}_{trans}_{i}".lower()
                    r=await owner.cmd(type="config/auth/create",name=f"mx {i}",group_ids=[gid],local_only=False)
                    uid=r["result"]["user"]["id"]
                    await owner.cmd(type="config/auth_provider/homeassistant/create",user_id=uid,username=u,password=PW)
                    mt=await login(s,u,PW)
                    if not mt: continue
                    m,_=await conn(mt)
                    if not m: continue
                    pre=await vector(m,owner,"pre")
                    if trans=="delete": await owner.cmd(type="config/auth/delete",user_id=uid)
                    else: await owner.cmd(type="config/auth/update",user_id=uid,is_active=False)
                    await asyncio.sleep(1.2)
                    post=await vector(m,owner,"post")
                    n+=1
                    for k in OPS:
                        pre_counts[k]+=pre[k]
                        counts[k]+= (pre[k] and post[k])
                    try: await m.ws.close()
                    except Exception: pass
                    if trans=="deactivate":
                        try: await owner.cmd(type="config/auth/delete",user_id=uid)
                        except Exception: pass
                results[arm]={"n":n,"pre":pre_counts,"residual":counts}
                log(f"  finished {arm}: n={n}")
        log("\n=== ROLE x TRANSITION x OPERATION MATRIX ===")
        for arm,d in results.items():
            n=d["n"]; log(f"\n  {arm}  (n={n} independent runs)")
            log(f"    {'operation':18s} {'pre':>5s} {'residual':>9s} {'prop':>7s}  95% CI")
            for k in OPS:
                if d["pre"][k]==0: log(f"    {k:18s} {0:5d} {'-':>9s} {'n/a':>7s}  (never available pre-transition)"); continue
                lo,hi=wilson(d["residual"][k], d["pre"][k])
                log(f"    {k:18s} {d['pre'][k]:5d} {d['residual'][k]:9d} {d['residual'][k]/d['pre'][k]:7.3f}  [{lo:.3f}, {hi:.3f}]")
        json.dump(results, open("/tmp/matrix_p1e7.json","w"))
asyncio.run(main())
