"""P2 EXPERIMENT 17 - does the established-connection residue appear on Homebridge UI?

The Home Assistant finding is not that the request path is broken - it is not -
but that a connection authenticated BEFORE removal keeps serving afterwards.
A prevalence claim therefore has to test the same shape elsewhere: request path
first (expected clean), then a persistent channel opened before the transition.

Homebridge UI authenticates with a bearer token and pushes live updates over
socket.io. Arms:
    request path, before removal      expect 200
    request path, after removal       expect 401 if the platform re-checks
    socket.io opened before removal   the question
"""
import asyncio, json, sys, time
import aiohttp, socketio

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8191"
log = lambda m: print(m, flush=True)

async def login(s, u, p):
    async with s.post(f"{BASE}/api/auth/login", json={"username": u, "password": p}) as r:
        if r.status != 201 and r.status != 200: return None
        return (await r.json()).get("access_token")

async def rest(s, tok, ep):
    try:
        async with s.get(f"{BASE}{ep}", headers={"Authorization": f"Bearer {tok}"},
                         timeout=aiohttp.ClientTimeout(total=8)) as r:
            return r.status
    except Exception:
        return 0

async def main():
    async with aiohttp.ClientSession() as s:
        atok = await login(s, "tsadmin", "AdminPass123")
        if not atok: log("FATAL: admin login failed"); sys.exit(2)
        # recreate the member (a previous run deleted it)
        async with s.post(f"{BASE}/api/users", headers={"Authorization": f"Bearer {atok}"},
                json={"name": "TS Member", "username": "tsmember2",
                      "password": "MemberPass123", "admin": False}) as r:
            j = await r.json(); uid = j.get("id")
        mtok = await login(s, "tsmember2", "MemberPass123")
        if not mtok: log("FATAL: member login failed"); sys.exit(2)
        log(f"  member created (id={uid}) and authenticated")

        # --- open a socket.io connection BEFORE removal ---
        events = []
        sio = socketio.AsyncClient(reconnection=False, logger=False, engineio_logger=False)

        @sio.event(namespace="/status")
        async def connect(): events.append(("connect", time.time()))
        @sio.event(namespace="/status")
        async def disconnect(): events.append(("disconnect", time.time()))
        @sio.on("*", namespace="/status")
        async def catch_all(ev, *a): events.append((ev, time.time()))

        connected = False
        try:
            await sio.connect(BASE, namespaces=["/status"], transports=["websocket"],
                              auth={"token": mtok}, wait_timeout=10)
            connected = sio.connected
        except Exception as e:
            log(f"  socket.io connect failed: {type(e).__name__}: {e}")

        log(f"\n  {'arm':44s} {'result'}")
        log(f"  {'-'*44} {'-'*22}")
        pre = await rest(s, mtok, "/api/status/homebridge")
        log(f"  {'request path, before removal':44s} HTTP {pre}")
        log(f"  {'socket.io opened before removal':44s} {'connected' if connected else 'NOT connected'}")
        if not connected:
            log("\n  Cannot test the established-connection arm: the socket never opened.")
            log("  Recording this platform as INCONCLUSIVE for the persistent-channel question.")
            await sio.disconnect() if sio.connected else None
            sys.exit(0)

        # baseline liveness: does the socket receive anything at all?
        await sio.emit("monitor-status", namespace="/status")
        await asyncio.sleep(4)
        base_ev = len(events)
        log(f"  {'socket events received before removal':44s} {base_ev}")

        # --- remove the member ---
        async with s.delete(f"{BASE}/api/users/{uid}", headers={"Authorization": f"Bearer {atok}"}) as r:
            log(f"\n  DELETE /api/users/{uid} -> HTTP {r.status}")
        await asyncio.sleep(3)

        post = await rest(s, mtok, "/api/status/homebridge")
        log(f"\n  {'request path, after removal':44s} HTTP {post}")
        still = sio.connected
        log(f"  {'socket.io still connected':44s} {still}")
        before = len(events)
        await sio.emit("monitor-status", namespace="/status")
        await asyncio.sleep(6)
        after = len(events)
        log(f"  {'socket events received after removal':44s} {after - before}")

        log("")
        if post == 401 and not still:
            log("  VERDICT: Homebridge UI closes both paths. Removal invalidates the issued")
            log("  token AND drops the established socket. This is a NEGATIVE result for the")
            log("  prevalence claim, and a useful one: the pattern is not universal.")
        elif post == 401 and still and (after - before) > 0:
            log("  VERDICT: SAME SHAPE AS HOME ASSISTANT. The request path re-checks and")
            log("  refuses, while a connection opened before the transition keeps delivering.")
            log("  This is a second witness for the connection-lifetime pattern.")
        elif post == 401 and still:
            log("  VERDICT: the socket object stayed open but delivered nothing after removal.")
            log("  Report as connection-open-but-silent; not equivalent to the HA residue.")
        else:
            log(f"  VERDICT: unexpected combination (rest={post}, socket={still}). Inspect above.")
        try: await sio.disconnect()
        except Exception: pass

asyncio.run(main())
