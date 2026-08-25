"""R3 follow-up: can a REMOVED user's still-open socket still READ / SUBSCRIBE?"""
import asyncio, json
import aiohttp, websockets

BASE="http://localhost:8124"; WS="ws://localhost:8124/api/websocket"; CID="http://localhost:8124/"
OWNER=("tsowner","Owner-Passw0rd-123")
log=lambda m: print(m, flush=True)

async def tok_from_code(s,c):
    async with s.post(f"{BASE}/auth/token", data={"grant_type":"authorization_code","code":c,"client_id":CID}) as r:
        return (await r.json())["access_token"]
async def login(s,u,p):
    async with s.post(f"{BASE}/auth/login_flow", json={"client_id":CID,"handler":["homeassistant",None],"redirect_uri":CID,"type":"authorize"}) as r:
        f=(await r.json())["flow_id"]
    async with s.post(f"{BASE}/auth/login_flow/{f}", json={"client_id":CID,"username":u,"password":p}) as r:
        return await tok_from_code(s,(await r.json())["result"])

class Conn:
    def __init__(s,ws): s.ws,s.id=ws,0
    async def cmd(s,**kw):
        s.id+=1; await s.ws.send(json.dumps({"id":s.id,**kw}))
        while True:
            m=json.loads(await asyncio.wait_for(s.ws.recv(),timeout=15))
            if m.get("id")==s.id and m["type"]=="result": return m
    async def drain(s,secs):
        out=[]; end=asyncio.get_event_loop().time()+secs
        while asyncio.get_event_loop().time()<end:
            try: out.append(json.loads(await asyncio.wait_for(s.ws.recv(),timeout=max(0.1,end-asyncio.get_event_loop().time()))))
            except (asyncio.TimeoutError,): break
        return out

async def connect(t):
    ws=await websockets.connect(WS,max_size=None)
    await ws.recv(); await ws.send(json.dumps({"type":"auth","access_token":t}))
    m=json.loads(await ws.recv())
    return (Conn(ws),m) if m["type"]=="auth_ok" else (None,m)

async def main():
    async with aiohttp.ClientSession() as s:
        otok=await login(s,*OWNER); owner,_=await connect(otok)
        r=await owner.cmd(type="config/auth/create",name="TS ReadProbe",group_ids=["system-users"],local_only=False)
        uid=r["result"]["user"]["id"]
        await owner.cmd(type="config/auth_provider/homeassistant/create",user_id=uid,username="member_read",password="Member-Passw0rd-123")
        tok=await login(s,"member_read","Member-Passw0rd-123")
        conn,_=await connect(tok); log(f"member socket authenticated (uid={uid})")

        pre=await conn.cmd(type="get_states")
        log(f"  CONTROL pre-delete  get_states: success={pre['success']} n={len(pre.get('result',[]))}")
        sub=await conn.cmd(type="subscribe_events",event_type="state_changed")
        log(f"  CONTROL pre-delete  subscribe : success={sub['success']}")

        d=await owner.cmd(type="config/auth/delete",user_id=uid)
        log(f"  DELETE issued: success={d['success']}"); await asyncio.sleep(2)

        try:
            post=await conn.cmd(type="get_states")
            log(f"  >>> POST-DELETE get_states: success={post['success']} n={len(post.get('result',[]))} err={post.get('error')}")
        except Exception as e:
            log(f"  >>> POST-DELETE get_states: connection dead ({type(e).__name__})"); return

        # does the pre-existing subscription still deliver events?
        await owner.cmd(type="call_service",domain="input_boolean",service="toggle",
                        target={"entity_id":"input_boolean.ts_probe"})
        evs=await conn.drain(3.0)
        sc=[e for e in evs if e.get("type")=="event" and e.get("event",{}).get("event_type")=="state_changed"]
        log(f"  >>> POST-DELETE events delivered on pre-existing subscription: {len(sc)}")
        if sc:
            ent=sc[0]["event"]["data"].get("entity_id")
            log(f"      e.g. entity_id={ent} new_state={sc[0]['event']['data'].get('new_state',{}).get('state')}")
        n2=await conn.cmd(type="subscribe_events",event_type="state_changed")
        log(f"  >>> POST-DELETE new subscribe_events: success={n2['success']} err={n2.get('error')}")
        log("")
        log(f"  READ RESIDUE: {post['success'] or len(sc)>0}")
        await conn.ws.close()
asyncio.run(main())
