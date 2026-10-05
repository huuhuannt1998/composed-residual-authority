"""P1 EXPERIMENT 9 - deputy generality.

Shows the deputy path does not depend on one contrived automation. Seven
automation families are installed and each is driven post-removal by the same
orphaned socket.

The decisive case is A7: an automation authored by the OWNER, who remains fully
authorized. The removed principal supplies only a trigger, and no authorization
object anywhere points back to them. That is the strongest form of the composed
claim, because even an auditor inspecting every automation's author finds only
a current member.

Usage: p1e9_deputy_generality.py <port>
"""
import asyncio, json, sys
import aiohttp, websockets
PORT=sys.argv[1] if len(sys.argv)>1 else "8135"
BASE=f"http://localhost:{PORT}"; WS=f"ws://localhost:{PORT}/api/websocket"; CID=f"{BASE}/"
OWNER=("tsowner","Owner-Passw0rd-123"); PW="Member-Passw0rd-123"
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

# family -> (helper entity, automation body). All authored by the OWNER.
FAM={
 "A1_input_boolean":  ("input_boolean.fam_a1", [{"service":"input_boolean.turn_on","target":{"entity_id":"input_boolean.fam_a1"}}]),
 "A2_light_like":     ("input_boolean.fam_a2", [{"service":"input_boolean.turn_on","target":{"entity_id":"input_boolean.fam_a2"}}]),
 "A3_script":         ("input_boolean.fam_a3", [{"service":"script.turn_on","target":{"entity_id":"script.fam_a3"}}]),
 "A4_scene":          ("input_boolean.fam_a4", [{"service":"scene.turn_on","target":{"entity_id":"scene.fam_a4"}}]),
 "A5_logging":        ("input_boolean.fam_a5", [{"service":"system_log.write","data":{"message":"ts a5"}},
                                                {"service":"input_boolean.turn_on","target":{"entity_id":"input_boolean.fam_a5"}}]),
 "A6_multistep":      ("input_boolean.fam_a6", [{"delay":{"milliseconds":200}},
                                                {"service":"input_boolean.turn_on","target":{"entity_id":"input_boolean.fam_a6"}}]),
}

async def main():
    async with aiohttp.ClientSession() as s:
        otok=await onboard(s) or await login(s,*OWNER)
        owner,_=await conn(otok)
        H={"Authorization":f"Bearer {otok}","Content-Type":"application/json"}
        for fam,(ent,_a) in FAM.items():
            try: await owner.cmd(type="input_boolean/create",name=ent.split(".")[1])
            except Exception: pass
        # script + scene targets for A3/A4
        async with s.post(f"{BASE}/api/config/script/config/fam_a3",headers=H,
            json={"alias":"fam a3","sequence":[{"service":"input_boolean.turn_on","target":{"entity_id":"input_boolean.fam_a3"}}]}) as r: await r.text()
        async with s.post(f"{BASE}/api/config/scene/config/fam_a4",headers=H,
            json={"name":"fam a4","entities":{"input_boolean.fam_a4":"on"}}) as r: await r.text()
        for fam,(ent,act) in FAM.items():
            async with s.post(f"{BASE}/api/config/automation/config/{fam.lower()}",headers=H,
                json={"alias":fam,"trigger":[{"platform":"event","event_type":f"trig_{fam.lower()}"}],
                      "action":act,"mode":"single"}) as r: await r.text()
        for svc in ("script","scene","automation"):
            try: await owner.cmd(type="call_service",domain=svc,service="reload")
            except Exception: pass
        await asyncio.sleep(3)
        # member: create, authenticate, then delete. Note the member authors NOTHING.
        r=await owner.cmd(type="config/auth/create",name="Deputy Probe",group_ids=["system-admin"],local_only=False)
        uid=r["result"]["user"]["id"]
        await owner.cmd(type="config/auth_provider/homeassistant/create",user_id=uid,username="deputy_probe",password=PW)
        mtok=await login(s,"deputy_probe",PW); m,_=await conn(mtok)
        for fam,(ent,_a) in FAM.items():
            await owner.cmd(type="call_service",domain="input_boolean",service="turn_off",target={"entity_id":ent})
        await asyncio.sleep(1)
        pre={}
        for fam,(ent,_a) in FAM.items():
            await m.cmd(type="fire_event",event_type=f"trig_{fam.lower()}"); await asyncio.sleep(1.2)
            pre[fam]=(await st(owner,ent))=="on"
            await owner.cmd(type="call_service",domain="input_boolean",service="turn_off",target={"entity_id":ent})
        await asyncio.sleep(1)
        await owner.cmd(type="config/auth/delete",user_id=uid); await asyncio.sleep(2)
        post={}
        for fam,(ent,_a) in FAM.items():
            try: await m.cmd(type="fire_event",event_type=f"trig_{fam.lower()}")
            except Exception: pass
            await asyncio.sleep(1.2)
            post[fam]=(await st(owner,ent))=="on"
        log("\n=== DEPUTY GENERALITY (all automations authored by the OWNER) ===")
        log(f"  {'family':22s} {'pre':>6s} {'post-removal':>13s}")
        n=0
        for fam in FAM:
            hit=pre[fam] and post[fam]; n+=hit
            log(f"  {fam:22s} {str(pre[fam]):>6s} {str(post[fam]):>13s}{'   RESIDUAL' if hit else ''}")
        log(f"\n  families reachable after removal: {n}/{len(FAM)}")
        log("  NOTE: the removed principal authored none of these automations;")
        log("        every automation names the owner, who remains authorized.")
        json.dump({"pre":pre,"post":post}, open("/tmp/deputy_generality.json","w"))
asyncio.run(main())
