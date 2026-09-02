"""P1 EXPERIMENT 8 (extended) - residual lifetime over long delays.

The short-delay arms are already run (p1e8_lifetime.py). This adds the delays the
review asks for and the termination events not previously covered. The decisive
point is +30 min: Home Assistant access tokens carry a 30-minute lifetime, so if
an established socket keeps working past it, the platform is not re-checking
token validity on an open connection.

Results are appended to /tmp/p1e8b_rows.json after EVERY probe, so a partial run
still yields usable rows.

Owner operations use a long-lived token so the observer outlives the subject.
"""
import asyncio, json, subprocess, sys, time
import aiohttp, websockets
PORT="8138"; BASE=f"http://localhost:{PORT}"; WS=f"ws://localhost:{PORT}/api/websocket"; CID=f"{BASE}/"
OWNER=("tsowner","Owner-Passw0rd-123"); PW="Member-Passw0rd-123"; EID="input_boolean.ts_probe"
ROWS="/tmp/p1e8b_rows.json"; rows=[]
log=lambda m: print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)
def save():
    json.dump(rows, open(ROWS,"w"), indent=1)
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
            m=json.loads(await asyncio.wait_for(s.ws.recv(),timeout=15))
            if m.get("id")==s.id and m["type"]=="result": return m
    async def drain(s,secs):
        out=[];end=asyncio.get_event_loop().time()+secs
        while asyncio.get_event_loop().time()<end:
            try: out.append(json.loads(await asyncio.wait_for(s.ws.recv(),timeout=max(0.1,end-asyncio.get_event_loop().time()))))
            except Exception: break
        return out
async def conn(t):
    try:
        ws=await websockets.connect(WS,max_size=None,ping_interval=20); await ws.recv()
        await ws.send(json.dumps({"type":"auth","access_token":t})); m=json.loads(await ws.recv())
        return (C(ws),m["type"]) if m["type"]=="auth_ok" else (None,m["type"])
    except Exception as e: return None,f"err:{type(e).__name__}"
async def st(c,e):
    r=await c.cmd(type="get_states")
    for x in (r.get("result") or []):
        if x["entity_id"]==e: return x["state"]
async def probe(label,m,owner):
    """socket alive / state read / event stream / indirect actuation"""
    v=dict(label=label,socket=False,read=False,stream=False,actuate=False)
    if m is None: rows.append(v); save(); log(f"  {label:28s} 0/0/0/0 (no socket)"); return v
    try:
        r=await m.cmd(type="get_states"); v["socket"]=True; v["read"]=len(r.get("result") or [])>0
    except Exception as e:
        # A dead socket is only a finding if we know WHY it died. Capture the
        # close code and reason, and the platform's own log, before anything
        # tears the container down and destroys the evidence.
        cc=getattr(m.ws,"close_code",None); cr=getattr(m.ws,"close_reason",None)
        v["close_code"]=cc; v["close_reason"]=str(cr) if cr else None
        v["exception"]=f"{type(e).__name__}: {e}"
        try:
            lg=subprocess.run(["docker","logs","--tail","40","tslife"],
                              capture_output=True,text=True,timeout=20)
            v["container_log_tail"]=(lg.stdout+lg.stderr)[-3000:]
        except Exception: pass
        rows.append(v); save()
        log(f"  {label:28s} 0/0/0/0 (socket dead: close_code={cc} reason={cr!r} {type(e).__name__})")
        return v
    try:
        await owner.cmd(type="call_service",domain="input_boolean",service="toggle",target={"entity_id":EID})
        v["stream"]=any(e.get("type")=="event" for e in await m.drain(1.8))
    except Exception: pass
    try:
        await owner.cmd(type="call_service",domain="input_boolean",service="turn_off",target={"entity_id":EID}); await asyncio.sleep(0.4)
        await m.cmd(type="fire_event",event_type="ts_deputy_trigger"); await asyncio.sleep(1.6)
        v["actuate"]=(await st(owner,EID))=="on"
    except Exception: pass
    rows.append(v); save()
    log(f"  {label:28s} {int(v['socket'])}/{int(v['read'])}/{int(v['stream'])}/{int(v['actuate'])}")
    return v
async def main():
    async with aiohttp.ClientSession() as s:
        otok=await onboard(s) or await login(s,*OWNER)
        owner,_=await conn(otok)
        try: await owner.cmd(type="input_boolean/create",name="ts probe")
        except Exception: pass
        await asyncio.sleep(1.2)
        # owner needs to outlive the 30-minute access-token lifetime
        r=await owner.cmd(type="auth/long_lived_access_token",client_name="ts-observer",lifespan=3)
        ollat=r.get("result")
        H={"Authorization":f"Bearer {otok}","Content-Type":"application/json"}
        async with s.post(f"{BASE}/api/config/automation/config/tsdeputy",headers=H,
            json={"alias":"ts deputy probe","trigger":[{"platform":"event","event_type":"ts_deputy_trigger"}],
                  "action":[{"service":"input_boolean.turn_on","target":{"entity_id":EID}}],"mode":"single"}) as r2: await r2.text()
        await owner.cmd(type="call_service",domain="automation",service="reload"); await asyncio.sleep(2)
        try: await owner.ws.close()
        except Exception: pass
        owner,_=await conn(ollat)          # observer on the long-lived token
        uid_r=await owner.cmd(type="config/auth/create",name="life subj",group_ids=["system-admin"],local_only=False)
        uid=uid_r["result"]["user"]["id"]
        await owner.cmd(type="config/auth_provider/homeassistant/create",user_id=uid,username="lifesubj",password=PW)
        mtok=await login(s,"lifesubj",PW)
        m,_=await conn(mtok)
        # register the durable subscription BEFORE the transition, otherwise the
        # event-stream column measures nothing (caught by the pre-deletion control
        # reading 0 on a channel that must be open)
        await m.cmd(type="subscribe_events",event_type="state_changed")
        await asyncio.sleep(0.5)
        await probe("pre-deletion control",m,owner)
        await owner.cmd(type="config/auth/delete",user_id=uid)
        log("subject DELETED; entering delay schedule")
        await asyncio.sleep(2)
        # Hourly from +2h. The previous schedule jumped +2h -> +6h, so when the
        # socket died somewhere in that window there was no way to say when or
        # why. A four-hour blind spot is not a measurement.
        sched=[("immediately",0),("+1 min",58),("+5 min",240),("+30 min",1500),
               ("+1 hour",1800),("+2 hours",3600),("+3 hours",3600),
               ("+4 hours",3600),("+5 hours",3600),("+6 hours",3600)]
        for label,wait in sched:
            if wait: await asyncio.sleep(wait)
            if owner is None or True:
                try: await owner.cmd(type="get_states")
                except Exception:
                    owner,_=await conn(ollat)          # re-establish the observer if it dropped
            await probe(label,m,owner)
        # ---- termination events -----------------------------------------------
        log("delay schedule complete; termination events")
        try:
            await owner.cmd(type="call_service",domain="automation",service="reload"); await asyncio.sleep(3)
            await probe("after automation reload",m,owner)
        except Exception: pass
        try:
            await owner.cmd(type="call_service",domain="homeassistant",service="reload_all"); await asyncio.sleep(6)
            await probe("after integration reload",m,owner)
        except Exception: rows.append(dict(label="after integration reload",note="unsupported")); save()
        subprocess.run(["docker","restart","tslife"],capture_output=True)
        await asyncio.sleep(45)
        await probe("after container restart",None,owner)
        log("DONE")
        save()
asyncio.run(main())
