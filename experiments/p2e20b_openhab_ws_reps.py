"""P2 EXPERIMENT 20b - replication of the openHAB established-websocket residue.

p2e20 measured it once. One trial on one version is an anecdote, so this repeats
the whole cycle N times inside a live container - create the member, mint a
token, establish the websocket, remove the member, re-probe - and reports the
distribution. Runs against whatever image is already up, so the same file serves
the version check (p2e20c) without modification.

Recorded per trial, all over ONE websocket held across the transition:
  read      events still arriving after removal
  direct    ItemCommandEvent -> TsProbe still lands after removal
  newconn   a NEW websocket on the removed token          (must be refused)
  restrest  a REST call on the removed token              (must be 401)

The last two are the controls that separate "the established session survives"
from "the token was never revoked at all". Without them the result would be
about token lifetime and would say nothing about session teardown.
"""
import asyncio, json, re, subprocess, sys, time, urllib.error, urllib.request
import websockets

BASE="http://localhost:8150/rest"; WSU="ws://localhost:8150/ws"
PROBE="TsProbe"; TRIALS=int(sys.argv[2]) if len(sys.argv)>2 else 5
log=lambda m: print(m, flush=True)

def console(cmd):
    out=subprocess.run(["docker","exec","tsohab","bash","-c",
        f"printf '%s\\nlogout\\n' \"{cmd}\" | /openhab/runtime/bin/client -p habopen 2>/dev/null"],
        capture_output=True,text=True).stdout
    return re.sub(r'\x1b\[[0-9;]*m','',out)

def rest(method,path,tok,body=None,ctype="application/json"):
    r=urllib.request.Request(BASE+path,method=method,
        data=(body if isinstance(body,bytes) else json.dumps(body).encode()) if body is not None else None)
    r.add_header("Authorization","Bearer "+tok)
    if body is not None: r.add_header("Content-Type",ctype)
    r.add_header("Accept","application/json")
    try:
        with urllib.request.urlopen(r,timeout=15) as f:
            t=f.read().decode(errors="ignore")
            try: return f.status,json.loads(t)
            except Exception: return f.status,t
    except urllib.error.HTTPError as e: return e.code,""
    except Exception: return 0,""

def st(adm):
    c,b=rest("GET",f"/items/{PROBE}",adm)
    return b.get("state") if c==200 and isinstance(b,dict) else f"?{c}"

def off(adm):
    rest("POST",f"/items/{PROBE}",adm,b"OFF","text/plain"); time.sleep(1.0)

async def cmd_probe(ws,eid):
    await ws.send(json.dumps({"type":"ItemCommandEvent",
        "topic":f"openhab/items/{PROBE}/command",
        "payload":json.dumps({"type":"OnOff","value":"ON"}),
        "eventId":eid,"source":"reps"}))
    got=[]
    for _ in range(6):
        try: got.append(json.loads(await asyncio.wait_for(ws.recv(),timeout=3)))
        except Exception: break
    return got

async def trial(i,adm,rows):
    user=f"ohmem{i}"
    console(f"openhab:users remove {user}")
    console(f"openhab:users add {user} MemberPass123 user")
    tok=None
    for _ in range(3):
        out=console(f"openhab:users addApiToken {user} tok{i} user")
        m=re.search(r'oh\.tok%d\.[A-Za-z0-9]+'%i,out)
        if m: tok=m.group(0); break
        time.sleep(1)
    if not tok:
        rows.append(dict(trial=i,valid=False,note="token mint failed")); log(f"  {i}  token mint FAILED"); return
    ws=await websockets.connect(f"{WSU}?accessToken={tok}",max_size=None)

    off(adm); await cmd_probe(ws,f"pre{i}"); time.sleep(1.2)
    pre = st(adm)=="ON"

    console(f"openhab:users remove {user}"); time.sleep(2.5)
    gone = user not in console("openhab:users list")

    off(adm); acks=await cmd_probe(ws,f"post{i}"); time.sleep(1.5)
    post = st(adm)=="ON"
    read = any(x.get("type","").startswith("Item") for x in acks)

    rc,_=rest("GET",f"/items/{PROBE}",tok)
    try:
        w2=await websockets.connect(f"{WSU}?accessToken={tok}",max_size=None); await w2.close(); newconn="ACCEPTED"
    except Exception: newconn="refused"
    await ws.close()

    v=dict(trial=i,valid=bool(pre and gone),pre=pre,post=post,read=read,
           rest_code=rc,newconn=newconn,user_gone=gone)
    rows.append(v)
    log(f"  {i}      {int(pre)}         {int(post)}        {int(read)}      "
        f"{rc:<5}{newconn:<10}{'RESIDUAL' if post else 'closed'}")

async def main():
    adm=sys.argv[1]; rows=[]
    rest("PUT",f"/items/{PROBE}",adm,{"type":"Switch","name":PROBE,"label":"TenantSafe probe"})
    time.sleep(2)
    log(f"\n=== openHAB established-websocket residue, {TRIALS} independent trials ===\n")
    log("  trial   pre   post-remove   read   REST  newconn   reading")
    for i in range(1,TRIALS+1): await trial(i,adm,rows)
    ok=[r for r in rows if r.get("valid")]
    res=[r for r in ok if r.get("post")]
    log(f"\n  valid trials                 : {len(ok)}/{TRIALS}")
    log(f"  direct actuation residual    : {len(res)}/{len(ok) if ok else 0}")
    log(f"  REST refused on removed token: {sum(1 for r in ok if r['rest_code']==401)}/{len(ok) if ok else 0}")
    log(f"  new websocket refused        : {sum(1 for r in ok if r['newconn']=='refused')}/{len(ok) if ok else 0}")
    json.dump(rows,open(f"../results/p2e20b_openhab_ws_reps.json","w"),indent=1)
asyncio.run(main())
