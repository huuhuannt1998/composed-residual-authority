"""P2 EXPERIMENT 20 - openHAB's ESTABLISHED WEBSOCKET, and whether a composed
residue exists on a second runtime.

Review W1: "The only depth-two witness in the entire study is the HA case",
and it asks for a second composed witness on a different runtime.

What the study already had on openHAB, and why it was not enough:
  p2e16  request path, API token. After `openhab:users remove` every arm - read,
         direct command, deputy rule - returns 401. openHAB looked clean.
  p2e16b/c  established SSE stream. Survives removal AND `clearSessions`, 5/5
         over two versions. But SSE is one-way, so it proves a READ residue and
         cannot actuate anything.

Neither touched the channel that matters. openHAB 4.1+ serves a BIDIRECTIONAL
websocket at /ws, and a client may push events onto the bus over it, which is
the structural analogue of Home Assistant's fire_event. So the question p2e16
should have asked is: does an ALREADY-ESTABLISHED websocket survive removal, and
if it does, what can the removed principal still cause through it?

Arms, all over ONE websocket opened BEFORE the transition and held across it.
TsProbe is the protected effect; TsSignal is a benign item the admin's rule
watches.

  read     events still arriving                     the SSE result, on /ws
  direct   ItemCommandEvent -> TsProbe                depth one if it lands
  composed ItemCommandEvent -> TsSignal -> rule -> TsProbe
                                                      depth two if THIS lands
                                                      while direct does not
  control  a NEW websocket on the removed token       must be refused, or the
                                                      finding is about token
                                                      lifetime, not sessions

Every outcome is reportable. If direct still lands, openHAB has a depth-one
residual actuation, which is a broader claim than the manuscript makes and NOT a
composed witness. If direct is refused and composed lands, that is the second
composed witness the review asks for. If the socket dies, openHAB tears down
established connections and the manuscript says so.

Observation of TsProbe is done with the ADMINISTRATOR's token throughout, so the
observer outlives the subject - the same discipline as p1e8d.
"""
import json, subprocess, sys, time, urllib.error, urllib.request
import asyncio, websockets

BASE = "http://localhost:8150/rest"
WS   = "ws://localhost:8150/ws"
PROBE, SIGNAL, RULE = "TsProbe", "TsSignal", "tsdeputy_signal"
log = lambda m: print(m, flush=True)

def console(cmd):
    import re
    out = subprocess.run(["docker","exec","tsohab","bash","-c",
        f"printf '%s\\nlogout\\n' \"{cmd}\" | /openhab/runtime/bin/client -p habopen 2>/dev/null"],
        capture_output=True, text=True).stdout
    return re.sub(r'\x1b\[[0-9;]*m','',out)

def req(method, path, tok=None, body=None):
    r = urllib.request.Request(BASE+path, method=method,
        data=json.dumps(body).encode() if body is not None else None)
    if tok:  r.add_header("Authorization","Bearer "+tok)
    if body is not None: r.add_header("Content-Type","application/json")
    r.add_header("Accept","application/json")
    try:
        with urllib.request.urlopen(r, timeout=15) as f:
            t = f.read().decode(errors="ignore")
            try: return f.status, json.loads(t)
            except Exception: return f.status, t
    except urllib.error.HTTPError as e: return e.code, e.read().decode(errors="ignore")[:120]
    except Exception as e: return 0, str(e)[:120]

def state(tok, item=PROBE):
    c,b = req("GET", f"/items/{item}", tok)
    return b.get("state") if c==200 and isinstance(b,dict) else f"?{c}"

def reset(tok):
    """Drive the protected item OFF with the admin's authority, so that finding
    it ON afterwards can only be the subject's doing."""
    req("POST", f"/items/{PROBE}", tok, None)
    r = urllib.request.Request(f"{BASE}/items/{PROBE}", method="POST", data=b"OFF")
    r.add_header("Authorization","Bearer "+tok); r.add_header("Content-Type","text/plain")
    try: urllib.request.urlopen(r, timeout=10)
    except Exception: pass
    time.sleep(1.2)

async def send(ws, item, value="ON", eid="e"):
    await ws.send(json.dumps({"type":"ItemCommandEvent",
        "topic": f"openhab/items/{item}/command",
        "payload": json.dumps({"type":"OnOff","value":value}),
        "eventId": eid, "source":"tsprobe"}))
    acks=[]
    for _ in range(6):
        try: acks.append(json.loads(await asyncio.wait_for(ws.recv(), timeout=3)))
        except Exception: break
    return acks

def ack_of(acks, eid):
    for a in acks:
        if a.get("type")=="WebSocketEvent" and a.get("eventId")==eid:
            return a.get("topic","").rsplit("/",1)[-1]      # success | failed | ...
    return None

async def arms(ws, adm, label, rows):
    v = dict(label=label)
    # read: is the channel still delivering events the admin causes?
    drained=[]
    async def listen(secs):
        end=asyncio.get_event_loop().time()+secs
        while asyncio.get_event_loop().time()<end:
            try: drained.append(json.loads(await asyncio.wait_for(ws.recv(),
                        timeout=max(0.1,end-asyncio.get_event_loop().time()))))
            except Exception: break
    reset(adm)
    t=asyncio.create_task(listen(2.5))
    r=urllib.request.Request(f"{BASE}/items/{SIGNAL}", method="POST", data=b"OFF")
    r.add_header("Authorization","Bearer "+adm); r.add_header("Content-Type","text/plain")
    try: urllib.request.urlopen(r,timeout=10)
    except Exception: pass
    await t
    v["read"] = any(x.get("type","").startswith("Item") for x in drained)

    # direct: command the protected item itself
    reset(adm)
    acks = await send(ws, PROBE, "ON", "direct")
    v["direct_ack"] = ack_of(acks, "direct")
    time.sleep(1.5)
    v["direct"] = state(adm)=="ON"

    # composed: command the benign item and let the admin's rule do the rest
    reset(adm)
    acks = await send(ws, SIGNAL, "ON", "composed")
    v["composed_ack"] = ack_of(acks, "composed")
    time.sleep(2.5)
    v["composed"] = state(adm)=="ON"

    rows.append(v)
    log(f"  {label:26s} read={int(bool(v['read']))} direct={int(bool(v['direct']))} "
        f"composed={int(bool(v['composed']))}   (acks {v['direct_ack']}/{v['composed_ack']})")
    return v

async def main():
    adm, mem = sys.argv[1], sys.argv[2]
    rows=[]
    log("\n=== openHAB 4.3.2 : established websocket, composed path ===\n")

    # Fixture, created here rather than assumed, so the experiment is
    # self-contained under run_all.sh: up_ohab builds TsProbe and its own
    # trigger-less rule, but the composed arm also needs the benign item the
    # admin's rule watches.
    for item,label in ((PROBE,"TenantSafe probe"),(SIGNAL,"TenantSafe signal")):
        req("PUT", f"/items/{item}", adm, {"type":"Switch","name":item,"label":label})
    time.sleep(2)

    # the deputy: a rule the ADMINISTRATOR owns, watching the benign item
    req("DELETE", f"/rules/{RULE}", adm)
    c,_ = req("POST","/rules", adm, {"uid":RULE,"name":"ts deputy signal",
        "triggers":[{"id":"t1","type":"core.ItemStateChangeTrigger",
                     "configuration":{"itemName":SIGNAL}}],
        "conditions":[],
        "actions":[{"id":"a1","type":"core.ItemCommandAction",
                    "configuration":{"itemName":PROBE,"command":"ON"}}]})
    log(f"  rule create -> http {c}")
    time.sleep(2)

    ws = await websockets.connect(f"{WS}?accessToken={mem}", max_size=None)
    log("  member websocket established BEFORE the transition")
    await arms(ws, adm, "pre-removal control", rows)

    log("\n  --- transition: openhab:users remove ohmember ---")
    console("openhab:users remove ohmember"); time.sleep(3)
    log(f"  users list now: {console('openhab:users list').strip().splitlines()[-1][:80]}")

    await arms(ws, adm, "after users remove", rows)

    log("\n  --- explicit teardown: clearSessions ---")
    console("openhab:users clearSessions ohmember"); time.sleep(3)
    await arms(ws, adm, "after clearSessions", rows)

    # control: a NEW connection on the removed principal's token must be refused
    log("")
    try:
        ws2 = await websockets.connect(f"{WS}?accessToken={mem}", max_size=None)
        await ws2.close(); newconn="ACCEPTED"
    except Exception as e:
        newconn=f"refused ({type(e).__name__})"
    log(f"  control: NEW websocket on the removed token -> {newconn}")
    rows.append(dict(label="new websocket on removed token", result=newconn))

    json.dump(rows, open("../results/p2e20_openhab_ws_composed.json","w"), indent=1)
    pre, post = rows[0], rows[1]
    log("\n=== VERDICT ===")
    for k in ("read","direct","composed"):
        pv, qv = bool(pre[k]), bool(post[k])
        log(f"  {k:9s} pre={int(pv)} post={int(qv)} -> "
            f"{'RESIDUAL' if pv and qv else ('closed' if pv else 'n/a')}")
    if post.get("composed") and not post.get("direct"):
        log("\n  DEPTH TWO on openHAB: direct effect refused, composed effect lands.")
    elif post.get("direct"):
        log("\n  DEPTH ONE on openHAB: the direct effect still lands. Not a composed witness.")
    elif post.get("read"):
        log("\n  READ-ONLY residue on openHAB, consistent with the SSE arm.")
    else:
        log("\n  NO residue on the established websocket.")

asyncio.run(main())
