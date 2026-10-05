"""P2 EXPERIMENT 17b - Homebridge UI, established push channels, counting DELIVERED events.

Why this replaces p2e17_homebridge.py for the socket question (D1 review, F-08).
The original probe counted every socket.io callback, including the namespace
`connect` callback, as an "event". Its "1 event before removal" was that connect
callback, and the message it emitted to provoke traffic ("monitor-status") is not a
message Homebridge UI handles, so nothing was ever delivered in either phase. The
socket arm therefore had no delivered-event baseline and could not answer the
question. This probe fixes that:

  * it speaks Engine.IO v4 / Socket.IO v5 directly over a websocket, so every
    frame is visible and only server-pushed EVENT packets ("42...") are counted;
  * it subscribes to two real push channels Homebridge UI 5.29.0 provides:
      /status  'monitor-server-status'  -> pushes 'homebridge-status' on each
                                           Homebridge server status change
      /log     'tail-log'               -> pushes 'stdout' with each log line
  * the stimulus is produced by the surviving administrator (PUT /api/server/restart),
    which changes the server status and writes log lines;
  * a delivered-event baseline is taken BEFORE removal, with the same stimulus and
    window; a trial whose baseline is zero on a channel is INVALID for that channel;
  * after removal, push delivery is measured BEFORE the subject sends anything,
    because Homebridge UI re-validates the user on each INCOMING message (WsGuard)
    and would disconnect the socket at that point; a request-response message is
    sent only afterwards, as a separate arm.

Subject: a non-admin member, as in the original arm. Usage:
    python3 p2e17b_homebridge_delivered.py <base-url> <out.json>
"""
import asyncio, json, sys, time
import aiohttp, websockets

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8191"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/tmp/p2e17b.json"
WSURL = BASE.replace("http://", "ws://") + "/socket.io/?EIO=4&transport=websocket"
WINDOW = 30.0          # seconds of observation after each stimulus
log = lambda m: print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


class NS:
    """One Engine.IO connection carrying one Socket.IO namespace. Counts frames."""
    def __init__(self, ns, token):
        self.ns, self.token = ns, token
        self.events = []          # (t, event_name) for server-pushed EVENT packets only
        self.payload_keys = []    # (t, event_name, sorted keys) for object payloads (values not kept)
        self.acks = {}            # ack id -> payload
        self.connected = False
        self.ns_disconnect = None # time a namespace DISCONNECT ("41") was received
        self.closed = None        # time the websocket itself closed
        self.connect_error = None
        self._ack = 0

    async def open(self):
        self.ws = await websockets.connect(WSURL, max_size=None, ping_interval=None)
        first = await self.ws.recv()              # engine.io OPEN: 0{...}
        assert first.startswith("0"), first
        await self.ws.send(f"40/{self.ns}," + json.dumps({"token": self.token}))
        while True:
            m = await asyncio.wait_for(self.ws.recv(), timeout=10)
            if m == "2": await self.ws.send("3"); continue
            if m.startswith(f"40/{self.ns},"): self.connected = True; break
            if m.startswith(f"44/{self.ns},"): self.connect_error = m; break
        self.reader = asyncio.create_task(self._read())
        return self.connected

    async def _read(self):
        pre = f"/{self.ns},"
        try:
            while True:
                m = await self.ws.recv()
                if m == "2":                       # engine.io ping -> pong (transport level, not guarded)
                    await self.ws.send("3"); continue
                if not m.startswith("4"): continue
                body = m[1:]
                kind, rest = body[0], body[1:]
                if rest.startswith(pre): rest = rest[len(pre):]
                if kind == "2":                    # EVENT pushed by the server
                    try:
                        arr = json.loads(rest); name = arr[0]
                        keys = sorted(arr[1].keys()) if len(arr) > 1 and isinstance(arr[1], dict) else None
                    except Exception: name, keys = "?", None
                    self.events.append((time.time(), name))
                    if keys is not None: self.payload_keys.append((time.time(), name, keys))
                elif kind == "3":                  # ACK: <id>[payload]
                    i = 0
                    while i < len(rest) and rest[i].isdigit(): i += 1
                    if i: self.acks[int(rest[:i])] = rest[i:]
                elif kind == "1":                  # namespace DISCONNECT from the server
                    self.ns_disconnect = time.time()
        except Exception:
            self.closed = time.time()

    async def emit(self, event, payload=None, ack=False):
        args = [event] + ([payload] if payload is not None else [])
        if ack:
            self._ack += 1
            await self.ws.send(f"42/{self.ns},{self._ack}" + json.dumps(args)); return self._ack
        await self.ws.send(f"42/{self.ns}," + json.dumps(args))

    def count(self, t0, t1, names=None):
        return sum(1 for t, n in self.events if t0 <= t < t1 and (names is None or n in names))

    def alive(self):
        return self.closed is None and self.ns_disconnect is None


async def main():
    res = {"base": BASE, "window_s": WINDOW, "subject_role": "non-admin member"}
    async with aiohttp.ClientSession() as s:
        async def login(u, p):
            async with s.post(f"{BASE}/api/auth/login", json={"username": u, "password": p}) as r:
                return (await r.json()).get("access_token") if r.status in (200, 201) else None
        async def rest(tok, ep):
            try:
                async with s.get(f"{BASE}{ep}", headers={"Authorization": f"Bearer {tok}"},
                                 timeout=aiohttp.ClientTimeout(total=8)) as r: return r.status
            except Exception: return 0
        async def restart(atok):
            async with s.put(f"{BASE}/api/server/restart", headers={"Authorization": f"Bearer {atok}"}, json={}) as r:
                return r.status

        atok = await login("tsadmin", "AdminPass123")
        if not atok: log("FATAL: admin login failed"); sys.exit(2)
        async with s.get(f"{BASE}/api/status/homebridge-version", headers={"Authorization": f"Bearer {atok}"}) as r:
            res["homebridge_version_endpoint"] = await r.text()
        async with s.post(f"{BASE}/api/users", headers={"Authorization": f"Bearer {atok}"},
                          json={"name": "TS Member", "username": "tsmember2", "password": "MemberPass123",
                                "admin": False}) as r:
            uid = (await r.json()).get("id")
        mtok = await login("tsmember2", "MemberPass123")
        if not mtok: log("FATAL: member login failed"); sys.exit(2)
        log(f"member created (id={uid}) and authenticated")

        st, lg = NS("status", mtok), NS("log", mtok)
        res["status_ns_connected"] = await st.open()
        res["log_ns_connected"] = await lg.open()
        log(f"namespaces connected: status={st.connected} log={lg.connected}"
            f"{'' if lg.connected else ' log error=' + str(lg.connect_error)}")
        if not (st.connected or lg.connected):
            res["verdict"] = "INVALID: no namespace connected"; json.dump(res, open(OUT, "w"), indent=1); sys.exit(1)

        # subscribe to the two push channels (these are the only messages the subject sends before removal,
        # apart from the request-response control below)
        if st.connected: await st.emit("monitor-server-status")
        if lg.connected: await lg.emit("tail-log", {"cols": 120, "rows": 40})
        await asyncio.sleep(5)                               # let the initial snapshot / log backlog arrive
        res["priming_events"] = {"status": len(st.events), "log": len(lg.events)}

        # request-response control BEFORE removal
        a = await st.emit("get-homebridge-status", ack=True); await asyncio.sleep(2)
        res["pre_request_response_ack"] = a in st.acks
        res["pre_request_path_http"] = await rest(mtok, "/api/status/homebridge")

        # ---- delivered-event BASELINE before removal -----------------------------------
        t0 = time.time(); res["pre_stimulus_http"] = await restart(atok)
        await asyncio.sleep(WINDOW); t1 = time.time()
        res["pre_delivered"] = {"status": st.count(t0, t1, {"homebridge-status"}),
                                "log": lg.count(t0, t1, {"stdout"})}
        log(f"BASELINE before removal: delivered status={res['pre_delivered']['status']} "
            f"log={res['pre_delivered']['log']} (restart HTTP {res['pre_stimulus_http']})")

        # ---- removal -----------------------------------------------------------------
        async with s.delete(f"{BASE}/api/users/{uid}", headers={"Authorization": f"Bearer {atok}"}) as r:
            res["delete_http"] = r.status
        log(f"DELETE /api/users/{uid} -> HTTP {res['delete_http']}")
        await asyncio.sleep(3)
        res["post_request_path_http"] = await rest(mtok, "/api/status/homebridge")
        res["post_alive_before_stimulus"] = {"status": st.alive(), "log": lg.alive()}

        # ---- delivery AFTER removal, subject silent ------------------------------------
        t2 = time.time(); res["post_stimulus_http"] = await restart(atok)
        await asyncio.sleep(WINDOW); t3 = time.time()
        res["post_delivered"] = {"status": st.count(t2, t3, {"homebridge-status"}),
                                 "log": lg.count(t2, t3, {"stdout"})}
        res["post_alive_after_stimulus"] = {"status": st.alive(), "log": lg.alive()}
        res["post_status_payload_keys"] = sorted({tuple(k) for t, n, k in st.payload_keys if t2 <= t < t3})
        log(f"AFTER removal (subject silent): delivered status={res['post_delivered']['status']} "
            f"log={res['post_delivered']['log']}; sockets alive {res['post_alive_after_stimulus']}")

        # ---- request-response AFTER removal (incoming message -> per-message guard) ------
        a2 = await st.emit("get-homebridge-status", ack=True); await asyncio.sleep(3)
        res["post_request_response_ack"] = a2 in st.acks
        res["post_alive_after_incoming"] = {"status": st.alive(), "log": lg.alive()}
        log(f"request path after removal: HTTP {res['post_request_path_http']}; "
            f"request-response ack after removal: {res['post_request_response_ack']}; "
            f"alive after incoming message: {res['post_alive_after_incoming']}")

        verdict = {}
        for ch in ("status", "log"):
            if res["pre_delivered"][ch] == 0: verdict[ch] = "INVALID (no delivered-event baseline)"
            elif res["post_delivered"][ch] > 0: verdict[ch] = "DELIVERS AFTER REMOVAL"
            else: verdict[ch] = "SILENT AFTER REMOVAL"
        res["verdict"] = verdict
        log(f"VERDICT per channel: {verdict}")
        json.dump(res, open(OUT, "w"), indent=1)
        for x in (st, lg):
            try: await x.ws.close()
            except Exception: pass

asyncio.run(main())
