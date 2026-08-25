"""P2 EXPERIMENT 16c - openHAB persistent-connection arm, repeated.

A single observation is not enough for a cross-platform claim. This runs N
independent trials, each with a freshly created user and a freshly opened SSE
stream, and additionally tests whether the explicit `clearSessions` teardown
closes the stream - the analogue of the Home Assistant refresh-token revocation
that DOES tear the socket down.
"""
import json, re, subprocess, sys, threading, time, urllib.request, urllib.error
BASE="http://localhost:8150/rest"; ITEM="TsProbe"
N=int(sys.argv[2]) if len(sys.argv)>2 else 5
log=lambda m: print(m, flush=True)
def console(cmd):
    out=subprocess.run(["docker","exec","tsohab","bash","-c",
        f"printf '%s\\nlogout\\n' \"{cmd}\" | /openhab/runtime/bin/client -p habopen 2>/dev/null"],
        capture_output=True,text=True).stdout
    return re.sub(r'\x1b\[[0-9;]*m','',out)
def post(path,tok,body):
    r=urllib.request.Request(BASE+path,method="POST",data=body)
    r.add_header("Authorization","Bearer "+tok); r.add_header("Content-Type","text/plain")
    try:
        with urllib.request.urlopen(r,timeout=10) as f: return f.status
    except urllib.error.HTTPError as e: return e.code
    except Exception: return 0
class SSE:
    def __init__(s,tok): s.tok=tok; s.events=[]; s.alive=None; s.stop=False; s.err=None
    def run(s):
        r=urllib.request.Request(BASE+"/events?topics=openhab/items/*/state")
        r.add_header("Authorization","Bearer "+s.tok); r.add_header("Accept","text/event-stream")
        try:
            f=urllib.request.urlopen(r,timeout=120); s.alive=True
            while not s.stop:
                line=f.readline()
                if not line: s.alive=False; break
                if line.startswith(b"data:"): s.events.append(time.time())
        except urllib.error.HTTPError as e: s.alive=False; s.err=f"http {e.code}"
        except Exception as e: s.alive=False; s.err=type(e).__name__
    def since(s,t): return sum(1 for ts in s.events if ts>t)
def toggle(adm,n=3):
    for i in range(n):
        post(f"/items/{ITEM}",adm,b"ON" if i%2==0 else b"OFF"); time.sleep(0.9)
def main():
    adm=sys.argv[1]; rows=[]
    log(f"\n=== openHAB persistent connection, {N} independent trials ===\n")
    log(f"  {'trial':6s} {'pre':>4s} {'post-remove':>12s} {'post-clearSessions':>19s}  reading")
    for i in range(N):
        u=f"ohrep{i}"
        console(f"openhab:users add {u} RepPass123 user")
        out=console(f"openhab:users addApiToken {u} rt{i} user")
        m=re.search(r'(oh\.rt\d+\.[A-Za-z0-9]+)',out)
        if not m:
            log(f"  {i:<6d} token issue; skipped"); continue
        tok=m.group(1)
        sse=SSE(tok); threading.Thread(target=sse.run,daemon=True).start(); time.sleep(2.5)
        t0=time.time(); toggle(adm); time.sleep(1.0); pre=sse.since(t0)
        console(f"openhab:users remove {u}"); time.sleep(2.5)
        t1=time.time(); toggle(adm); time.sleep(1.2); post1=sse.since(t1)
        console(f"openhab:users clearSessions {u}"); time.sleep(2.5)
        t2=time.time(); toggle(adm); time.sleep(1.2); post2=sse.since(t2)
        sse.stop=True
        rd = "INVALID (no pre events)" if pre==0 else ("RESIDUAL" if post1>0 else "closed at removal")
        log(f"  {i:<6d} {pre:>4d} {post1:>12d} {post2:>19d}  {rd}")
        rows.append(dict(trial=i,pre=pre,post_remove=post1,post_clear=post2,reading=rd))
    valid=[r for r in rows if r["pre"]>0]
    res=[r for r in valid if r["post_remove"]>0]
    clr=[r for r in valid if r["post_clear"]>0]
    log(f"\n  valid trials              : {len(valid)}/{len(rows)}")
    log(f"  residual after remove     : {len(res)}/{len(valid)}")
    log(f"  still residual after clearSessions : {len(clr)}/{len(valid)}")
    json.dump(rows,open("/tmp/p2e16c_reps.json","w"),indent=1)
if __name__=="__main__": main()
