"""E6.3 — does TSMON close the gate-identified residues?
Re-runs the deputy (EXIT-A) and read probes against the patched HA."""
import asyncio, json, time
import aiohttp, websockets
BASE="http://localhost:8124"; WS="ws://localhost:8124/api/websocket"; CID="http://localhost:8124/"
OWNER=("tsowner","Owner-Passw0rd-123"); PW="Member-Passw0rd-123"; EID="input_boolean.ts_probe"
log=lambda m: print(m, flush=True)
async def tokc(s,c):
    async with s.post(f"{BASE}/auth/token",data={"grant_type":"authorization_code","code":c,"client_id":CID}) as r: return await r.json()
async def onboard(s):
    """The runner supplies a FRESH instance, so create the owner rather than
    assuming one exists. Logging in blind against a clean container fails with
    invalid_auth, which reads as an auth defect rather than missing setup."""
    async with s.post(f"{BASE}/api/onboarding/users",json={"client_id":CID,"name":"TS Owner",
        "username":OWNER[0],"password":OWNER[1],"language":"en"}) as r:
        if r.status!=200: return None
        code=(await r.json())["auth_code"]
    t=(await tokc(s,code))["access_token"]
    for st in ("core_config","analytics"):
        async with s.post(f"{BASE}/api/onboarding/{st}",headers={"Authorization":f"Bearer {t}"}) as r:
            await r.text()
    return t

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
    async with aiohttp.ClientSession() as s:
        otok=await onboard(s) or await login(s,*OWNER); owner,_=await conn(otok); log("owner connected (TSMON active)")
        # Written against an instance where an earlier experiment had already
        # created the probe entity. On a fresh container it does not exist, so
        # actuation cannot be observed and the result reads as "no residue"
        # rather than "no measurement".
        try: await owner.cmd(type="input_boolean/create",name="ts probe")
        except Exception: pass
        await asyncio.sleep(1.2)
        auto={"alias":"ts deputy probe","trigger":[{"platform":"event","event_type":"ts_deputy_trigger"}],
              "action":[{"service":"input_boolean.turn_on","target":{"entity_id":EID}}],"mode":"single"}
        async with s.post(f"{BASE}/api/config/automation/config/tsdeputy",
            headers={"Authorization":f"Bearer {otok}","Content-Type":"application/json"},json=auto) as r: await r.text()
        await owner.cmd(type="call_service",domain="automation",service="reload"); await asyncio.sleep(2)
        # The necessity test (E3.4 arm 12) left this automation DISABLED and the state
        # survived the restart, which silently invalidated the first control. Force it on.
        await owner.cmd(type="call_service",domain="automation",service="turn_on",
                        target={"entity_id":"automation.ts_deputy_probe"})
        await asyncio.sleep(1.5)
        st_auto=await state(owner,"automation.ts_deputy_probe")
        log(f"  automation.ts_deputy_probe = {st_auto}")

        r=await owner.cmd(type="config/auth/create",name="TSMON probe",group_ids=["system-admin"],local_only=False)
        uid=r["result"]["user"]["id"]
        await owner.cmd(type="config/auth_provider/homeassistant/create",user_id=uid,username="member_tsmon2",password=PW)
        mtok=await login(s,"member_tsmon2",PW); m,_=await conn(mtok)

        await owner.cmd(type="call_service",domain="input_boolean",service="turn_off",target={"entity_id":EID}); await asyncio.sleep(0.5)
        ev=await m.cmd(type="fire_event",event_type="ts_deputy_trigger"); await asyncio.sleep(2)
        gs=await m.cmd(type="get_states")
        log(f"  CONTROL pre-removal : fire_event={ev['success']} entity={await state(owner,EID)} get_states n={len(gs.get('result') or [])}")

        await owner.cmd(type="call_service",domain="input_boolean",service="turn_off",target={"entity_id":EID}); await asyncio.sleep(0.5)
        await owner.cmd(type="config/auth/delete",user_id=uid); await asyncio.sleep(2)

        try:
            ev2=await m.cmd(type="fire_event",event_type="ts_deputy_trigger"); await asyncio.sleep(2)
            st=await state(owner,EID)
            gs2=await m.cmd(type="get_states")
            n2=len(gs2.get("result") or [])
            log(f"  POST-REMOVAL        : fire_event success={ev2.get('success')} err={(ev2.get('error') or {}).get('code')}")
            log(f"  POST-REMOVAL        : {EID}={st}   get_states n={n2}")
            log("")
            log(f"  >>> E6.3 DEPUTY residue closed : {st!='on'}")
            log(f"  >>> E6.3 READ   residue closed : {n2==0}")
        except Exception as e:
            log(f"  socket dead: {type(e).__name__}")

        # --- E6.4 overhead: per-decision latency of an admin-gated command ---
        r=await owner.cmd(type="config/auth/create",name="TSMON bench",group_ids=["system-admin"],local_only=False)
        buid=r["result"]["user"]["id"]
        await owner.cmd(type="config/auth_provider/homeassistant/create",user_id=buid,username="member_bench2",password=PW)
        btok=await login(s,"member_bench2",PW); b,_=await conn(btok)
        lat=[]
        for _ in range(300):
            t0=time.perf_counter(); await b.cmd(type="fire_event",event_type="ts_bench"); lat.append((time.perf_counter()-t0)*1000)
        lat.sort()
        log(f"\n  E6.4 fire_event latency WITH TSMON (n=300): median={lat[150]:.3f} ms  p99={lat[296]:.3f} ms  min={lat[0]:.3f}")
        json.dump(lat, open("/tmp/tsmon_lat.json","w"))
        await b.ws.close(); await owner.ws.close()
asyncio.run(main())
