"""P2 EXPERIMENT 16b - openHAB PERSISTENT-CONNECTION arm.

The request-path arm (p2e16_openhab.py) found openHAB clean: after
`openhab:users remove`, the API token is refused 401 on every request. But Home
Assistant is ALSO clean on its request paths - a deleted principal cannot
authenticate a new WebSocket. HA's defect lives only in the ALREADY-ESTABLISHED
connection. So the fair comparison is openHAB's established connection: a live
Server-Sent Events stream opened BEFORE the transition.

This arm holds an SSE stream open across the removal and asks whether events keep
arriving. That is the exact analogue of HA's orphaned socket.
"""
import json, subprocess, sys, threading, time, urllib.request, urllib.error
BASE="http://localhost:8150/rest"; ITEM="TsProbe"
log=lambda m: print(m, flush=True)
def console(cmd):
    import re
    out=subprocess.run(["docker","exec","tsohab","bash","-c",
        f"printf '%s\\nlogout\\n' \"{cmd}\" | /openhab/runtime/bin/client -p habopen 2>/dev/null"],
        capture_output=True,text=True).stdout
    return re.sub(r'\x1b\[[0-9;]*m','',out)
def post(path,tok,body,ctype="text/plain"):
    r=urllib.request.Request(BASE+path,method="POST",data=body if isinstance(body,bytes) else body.encode())
    r.add_header("Authorization","Bearer "+tok); r.add_header("Content-Type",ctype)
    try:
        with urllib.request.urlopen(r,timeout=10) as f: return f.status
    except urllib.error.HTTPError as e: return e.code
    except Exception: return 0
class SSE:
    def __init__(s,tok):
        s.tok=tok; s.events=[]; s.alive=None; s.stop=False; s.err=None
    def run(s):
        r=urllib.request.Request(BASE+"/events?topics=openhab/items/*/state")
        r.add_header("Authorization","Bearer "+s.tok); r.add_header("Accept","text/event-stream")
        try:
            f=urllib.request.urlopen(r,timeout=90); s.alive=True
            while not s.stop:
                line=f.readline()
                if not line: s.alive=False; break
                if line.startswith(b"data:"): s.events.append((time.time(),line[5:80]))
        except urllib.error.HTTPError as e: s.alive=False; s.err=f"http {e.code}"
        except Exception as e: s.alive=False; s.err=type(e).__name__
    def count_since(s,t): return sum(1 for ts,_ in s.events if ts>t)
def main():
    adm=sys.argv[1]; mem=sys.argv[2]
    log("\n=== openHAB persistent-connection (SSE) arm ===\n")
    sse=SSE(mem); th=threading.Thread(target=sse.run,daemon=True); th.start()
    time.sleep(3)
    log(f"  stream opened: alive={sse.alive} err={sse.err}")
    def toggle(n=3):
        for i in range(n):
            post(f"/items/{ITEM}",adm,b"ON" if i%2==0 else b"OFF"); time.sleep(0.9)
    t0=time.time(); toggle(); time.sleep(1.2)
    pre=sse.count_since(t0)
    log(f"  PRE-removal   : {pre} state events delivered to the member's stream")
    log("\n  --- transition: openhab:users remove ohmember2 ---")
    console("openhab:users remove ohmember2"); time.sleep(3)
    t1=time.time(); toggle(); time.sleep(1.5)
    post_n=sse.count_since(t1)
    log(f"  POST-removal  : {post_n} state events delivered   (stream alive={sse.alive} err={sse.err})")
    log("\n=== VERDICT ===")
    if pre==0:
        log("  INVALID: the pre-removal control delivered no events; instrument, not platform.")
    elif post_n>0:
        log(f"  RESIDUAL: the established SSE stream kept delivering {post_n} events after removal.")
        log("  openHAB reproduces the Home Assistant pattern on the persistent-connection path.")
    else:
        log("  CLOSED: the established stream stopped at removal.")
        log("  openHAB tears down live connections on removal; Home Assistant does not.")
    json.dump({"pre":pre,"post":post_n,"alive":sse.alive,"err":sse.err},
              open("/tmp/p2e16b_sse.json","w"),indent=1)
    sse.stop=True
if __name__=="__main__": main()
