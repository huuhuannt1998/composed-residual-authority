"""Decisive test: does an undrained subscribed socket die of max_queue backpressure?

Two sockets, identical except that one is drained continuously. Both subscribe
to state_changed, both use the library's keepalive. Push >max_queue events, then
wait past ping_timeout and see which is alive. If backpressure stops pongs being
processed, the undrained socket dies with 1011 and the drained one lives.
"""
import asyncio, json, sys, aiohttp, websockets
BASE="http://172.17.0.2:8123"; WS="ws://172.17.0.2:8123/api/websocket"; CID=f"{BASE}/"
OWNER=("tsowner","Owner-Passw0rd-123"); EID="input_boolean.ts_probe"
async def login(s,u,p):
    async with s.post(f"{BASE}/auth/login_flow",json={"client_id":CID,"handler":["homeassistant",None],"redirect_uri":CID,"type":"authorize"}) as r: f=(await r.json())["flow_id"]
    async with s.post(f"{BASE}/auth/login_flow/{f}",json={"client_id":CID,"username":u,"password":p}) as r:
        j=await r.json()
        if "result" not in j: print("login failed:",j); return None
    async with s.post(f"{BASE}/auth/token",data={"grant_type":"authorization_code","code":j["result"],"client_id":CID}) as r:
        return (await r.json())["access_token"]
async def conn(t,**kw):
    ws=await websockets.connect(WS,max_size=None,ping_interval=20,ping_timeout=20,close_timeout=10,**kw)
    await ws.recv(); await ws.send(json.dumps({"type":"auth","access_token":t}))
    m=json.loads(await ws.recv())
    assert m["type"]=="auth_ok", m
    return ws
async def cmd(ws,i,**kw):
    await ws.send(json.dumps({"id":i,**kw}))
async def main():
    async with aiohttp.ClientSession() as s:
        tok=await login(s,*OWNER)
        if not tok: sys.exit("no token")
        drv=await conn(tok)                       # driver: generates the events
        a  =await conn(tok)                       # UNDRAINED, subscribed
        b  =await conn(tok)                       # DRAINED,   subscribed
        await cmd(a,1,type="subscribe_events",event_type="state_changed")
        await cmd(b,1,type="subscribe_events",event_type="state_changed")
        await asyncio.sleep(1)
        stop=asyncio.Event()
        async def drain_b():
            while not stop.is_set():
                try: await asyncio.wait_for(b.recv(),timeout=1)
                except asyncio.TimeoutError: pass
                except Exception: return
        dt=asyncio.create_task(drain_b())
        print("pushing 60 state_changed events (max_queue=16)...")
        for i in range(60):
            await cmd(drv,100+i,type="call_service",domain="input_boolean",
                      service="toggle",target={"entity_id":EID})
            await asyncio.sleep(0.12)
        print("events pushed. waiting 90s (> ping_interval 20 + ping_timeout 20)...")
        for k in range(9):
            await asyncio.sleep(10)
            print("   t+%02ds  A(undrained) closed=%-5s code=%-5s | B(drained) closed=%-5s code=%s"
                  % (10*(k+1), a.state.name!='OPEN', getattr(a,'close_code',None),
                     b.state.name!='OPEN', getattr(b,'close_code',None)))
        stop.set(); await asyncio.sleep(1.2); dt.cancel()
        print()
        print("RESULT  A undrained: close_code=%s  reason=%r" % (getattr(a,'close_code',None), getattr(a,'close_reason',None)))
        print("RESULT  B drained  : close_code=%s  reason=%r" % (getattr(b,'close_code',None), getattr(b,'close_reason',None)))
asyncio.run(main())
