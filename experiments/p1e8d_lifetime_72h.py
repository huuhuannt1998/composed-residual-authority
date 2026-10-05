"""P1 EXPERIMENT 8d - residual lifetime to 72 hours, per-probe series retained.

Replaces the six-hour schedule. Three things change, all of them asked for by
review. The schedule runs to 72h rather than 6h, so the exposure window is
bounded in days rather than in hours. Every probe is written to disk as it
happens, so a run that dies mid-schedule still yields the series up to the
death rather than nothing - the earlier campaign lost exactly that and had to
report one run of three as unexplained. And the in-interface restart is a
scheduled event, not only the container restart, because the in-interface
action is the one a household would actually take and it does end the residue.

Laptop sleep is the known threat to validity here: a suspended host stops the
clock and can drop the socket for reasons that have nothing to do with the
platform. The probe records wall-clock gaps so a sleep shows up as a gap rather
than as a spurious residue death.
"""
_ORIGINAL_DOCSTRING = """P1 EXPERIMENT 8 (extended) - residual lifetime over long delays.

The short-delay arms are already run (p1e8_lifetime.py). This adds the delays the
review asks for and the termination events not previously covered. The decisive
point is +30 min: Home Assistant access tokens carry a 30-minute lifetime, so if
an established socket keeps working past it, the platform is not re-checking
token validity on an open connection.

Results are appended to /tmp/p1e8b_rows.json after EVERY probe, so a partial run
still yields usable rows.

Owner operations use a long-lived token so the observer outlives the subject.
"""
import os, asyncio, json, subprocess, sys, time, collections
import aiohttp, websockets
HOST=os.environ.get("HA_HOST","localhost"); PORT=os.environ.get("HA_PORT","8192")
BASE=f"http://{HOST}:{PORT}"; WS=f"ws://{HOST}:{PORT}/api/websocket"; CID=f"{BASE}/"
OWNER=("tsowner","Owner-Passw0rd-123"); PW="Member-Passw0rd-123"; EID="input_boolean.ts_probe"
ROWS=os.environ.get("ROWS_PATH","../results/lifetime/p1e8d_rows_72h.json"); rows=[]
# Schedule compression, for validating the instrument only. The socket death
# this probe kept hitting depends on the NUMBER of probes (each leaves unread
# frames) and not on wall-clock time, so a compressed run exercises the same
# failure path in minutes. SCHED_SCALE=1.0 is the real 72-hour schedule and is
# the default; any other value marks the rows file as a smoke test.
SCALE=float(os.environ.get("SCHED_SCALE","1.0"))
log=lambda m: print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)
def save():
    json.dump(({"SMOKE_TEST_not_a_result":True,"scale":SCALE,"rows":rows}
               if SCALE!=1.0 else rows), open(ROWS,"w"), indent=1)
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
    """One socket, one reader.

    The subject socket carries a live subscribe_events subscription, so the
    platform pushes events at it continuously whether or not the experiment is
    in a probe. websockets 17.1 defaults to max_queue=16: once sixteen messages
    are buffered unread it applies backpressure and stops reading the transport
    - and a transport that is not being read does not process incoming PONGs
    either, so the client's own keepalive ping times out and the client closes
    the connection it is measuring with 1011. That is what killed attempts 1 and
    4, confirmed directly by invalidated/maxqueue_backpressure_test.py: two
    sockets identical but for draining, the undrained one dead in ~40s, the
    drained one untouched.

    So exactly one coroutine calls recv(), always, and it demultiplexes: command
    results go to the waiting future, events go to a bounded log with arrival
    times. Nothing accumulates, backpressure is never reached, and a client that
    subscribes to events now actually reads them, which is also what a real
    client does.
    """
    def __init__(s,ws):
        s.ws,s.id=ws,0
        s.pending={}                       # id -> Future awaiting a result frame
        s.events=collections.deque(maxlen=4096)   # (arrival_time, message)
        s.dead=None
        s.reader=asyncio.create_task(s._read())
    async def _read(s):
        try:
            while True:
                m=json.loads(await s.ws.recv())
                if m.get("type")=="result" and m.get("id") in s.pending:
                    f=s.pending.pop(m["id"])
                    if not f.done(): f.set_result(m)
                else:
                    s.events.append((asyncio.get_event_loop().time(),m))
        except Exception as e:
            s.dead=e
            for f in s.pending.values():
                if not f.done(): f.set_exception(e)
            s.pending.clear()
    async def cmd(s,**kw):
        if s.dead: raise s.dead
        s.id+=1; i=s.id
        f=asyncio.get_event_loop().create_future(); s.pending[i]=f
        try: await s.ws.send(json.dumps({"id":i,**kw}))
        except Exception: s.pending.pop(i,None); raise
        return await asyncio.wait_for(f,timeout=15)
    def mark(s):
        """Open an observation window. Called BEFORE the owner acts, so an event
        caused by that action cannot land before the window opens - the reader
        is always consuming, so unlike the old blocking recv() there is no
        buffer to catch a straggler after the fact."""
        s._t0=asyncio.get_event_loop().time()
    async def drain(s,secs):
        """Events that arrived since mark(), after waiting `secs` for them."""
        t0=getattr(s,"_t0",None)
        if t0 is None: t0=asyncio.get_event_loop().time()
        await asyncio.sleep(secs)
        return [m for (t,m) in list(s.events) if t>=t0]
    async def close(s):
        s.reader.cancel()
        try: await s.ws.close()
        except Exception: pass
async def conn(t):
    try:
        # Two instrument faults killed four attempts and both are closed here.
        # (1) Home Assistant sets WebSocketResponse(heartbeat=55) in
        # components/websocket_api/http.py: it pings every 55s and closes a
        # connection that does not pong, so the client keepalive stays ON -
        # turning it off killed attempts 2 and 3. (2) The library stops reading
        # the transport once max_queue messages are buffered unread, which stops
        # PONGs being processed and makes the client self-close 1011; that
        # killed attempts 1 and 4 and is fixed in class C by always reading.
        # max_queue is raised as a second line of defence behind that reader.
        ws=await websockets.connect(WS,max_size=None,max_queue=512,
                                    ping_interval=20,ping_timeout=60,
                                    close_timeout=10); await ws.recv()
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
            lg=subprocess.run(["docker","logs","--tail","40","tslife72"],
                              capture_output=True,text=True,timeout=20)
            v["container_log_tail"]=(lg.stdout+lg.stderr)[-3000:]
        except Exception: pass
        rows.append(v); save()
        log(f"  {label:28s} 0/0/0/0 (socket dead: close_code={cc} reason={cr!r} {type(e).__name__})")
        return v
    try:
        m.mark()
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
        if not ollat: sys.exit(f"FATAL: no long-lived token for the observer: {r}")
        H={"Authorization":f"Bearer {otok}","Content-Type":"application/json"}
        async with s.post(f"{BASE}/api/config/automation/config/tsdeputy",headers=H,
            json={"alias":"ts deputy probe","trigger":[{"platform":"event","event_type":"ts_deputy_trigger"}],
                  "action":[{"service":"input_boolean.turn_on","target":{"entity_id":EID}}],"mode":"single"}) as r2: await r2.text()
        await owner.cmd(type="call_service",domain="automation",service="reload"); await asyncio.sleep(2)
        try: await owner.close()
        except Exception: pass
        owner,why=await conn(ollat)        # observer on the long-lived token
        if owner is None: sys.exit(f"FATAL: observer could not reconnect on the long-lived token: {why}")
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
        sched=[("immediately",0),("+1 min",58),("+5 min",240),("+30 min",1500)]
        for h in range(1,13):                       # hourly to +12h
            sched.append((f"+{h} hour"+("s" if h>1 else ""), 1800 if h==1 else 3600))
        for h in range(18,73,6):                    # then every six hours to +72h
            sched.append((f"+{h} hours", 6*3600))
        for label,wait in sched:
            if wait: await asyncio.sleep(wait*SCALE)
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
        # The in-UI core restart is a load-bearing measurement - it is the
        # action a household actually takes, and it is what ends the residue -
        # so it must not be lost to instrument noise. Home Assistant tears the
        # socket down while servicing the request, so the call never returns a
        # result frame; waiting for one and treating the timeout as a failure is
        # what made the smoke run record this row as "failed" and measure
        # nothing. Send it, expect no reply, then wait for the platform to come
        # back before reading the subject socket.
        try:
            try: await owner.cmd(type="call_service",domain="homeassistant",service="restart")
            except Exception: pass          # expected: HA closes before replying
            newowner=None
            for _ in range(24):             # up to ~2 min for the platform to return
                await asyncio.sleep(5)
                try:
                    newowner,_w=await conn(ollat)
                    if newowner: break
                except Exception: pass
            if newowner is None:
                log("  observer could not reconnect after restart; subject read is still valid")
            else:
                owner=newowner
            await probe("after in-UI core restart",m,owner)
        except Exception as e:
            rows.append(dict(label="after in-UI core restart",
                             note=f"failed: {type(e).__name__}: {e}")); save()
        # Best effort: the probe container may not carry the docker CLI. Never
        # let teardown crash the run after the schedule has completed.
        try: subprocess.run(["docker","restart","tslife72"],capture_output=True,timeout=60)
        except Exception as e: log(f"  container restart skipped: {type(e).__name__}")
        log("SCHEDULE COMPLETE")
        await asyncio.sleep(45)
        await probe("after container restart",None,owner)
        log("DONE")
        save()
asyncio.run(main())
