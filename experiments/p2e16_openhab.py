"""P2 EXPERIMENT 16 - second runtime ecosystem (openHAB 4.3.2).

Software-only, no hardware: virtual Items and a Rule stand in for devices, which
is exactly what the review permits ("virtual devices; software-only endpoints;
local emulation").

WHY openHAB IS THE RIGHT SECOND CASE. Its console exposes BOTH
    openhab:users remove <id>          (the transition)
    openhab:users clearSessions <id>   (a separate, explicit session teardown)
which is the same structural split Home Assistant has between deleting a user and
revoking a refresh token. If removal does not imply session teardown here either,
the phenomenon is not a Home Assistant implementation quirk.

Measured per arm: read items, command an item directly, and drive a Rule
(the deputy path), using the removed principal's still-held API token.
"""
import json, subprocess, sys, time, urllib.error, urllib.request
BASE="http://localhost:8150/rest"
ITEM="TsProbe"; RULE="tsdeputy"
log=lambda m: print(m, flush=True)
def console(cmd):
    out=subprocess.run(["docker","exec","tsohab","bash","-c",
        f"printf '%s\\nlogout\\n' \"{cmd}\" | /openhab/runtime/bin/client -p habopen 2>/dev/null"],
        capture_output=True,text=True).stdout
    import re; return re.sub(r'\x1b\[[0-9;]*m','',out)
def req(method,path,tok=None,body=None,ctype="application/json"):
    r=urllib.request.Request(BASE+path,method=method,
        data=(body if isinstance(body,bytes) else json.dumps(body).encode()) if body is not None else None)
    if tok: r.add_header("Authorization","Bearer "+tok)
    if body is not None: r.add_header("Content-Type",ctype)
    r.add_header("Accept","application/json")
    try:
        with urllib.request.urlopen(r,timeout=15) as f:
            t=f.read().decode(errors="ignore")
            try: return f.status,json.loads(t)
            except Exception: return f.status,t
    except urllib.error.HTTPError as e: return e.code,e.read().decode(errors="ignore")[:120]
    except Exception as e: return 0,str(e)[:120]
def state(tok):
    c,b=req("GET",f"/items/{ITEM}",tok)
    return b.get("state") if isinstance(b,dict) else None
def probe(label,tok,admtok):
    """read / direct command / rule-driven (deputy) actuation"""
    c1,_=req("GET","/items",tok);           read = c1==200
    req("POST",f"/items/{ITEM}",admtok,b"OFF",ctype="text/plain"); time.sleep(0.6)
    c2,_=req("POST",f"/items/{ITEM}",tok,b"ON",ctype="text/plain"); time.sleep(0.8)
    direct = (c2 in (200,202)) and state(admtok)=="ON"
    req("POST",f"/items/{ITEM}",admtok,b"OFF",ctype="text/plain"); time.sleep(0.6)
    c3,_=req("POST",f"/rules/{RULE}/runnow",tok); time.sleep(1.2)
    deputy = (c3 in (200,202)) and state(admtok)=="ON"
    log(f"  {label:34s} read={int(read)}  direct={int(direct)}  deputy={int(deputy)}   (http {c1}/{c2}/{c3})")
    return dict(label=label,read=read,direct=direct,deputy=deputy,http=[c1,c2,c3])
def main():
    adm=sys.argv[1]; mem=sys.argv[2]; rows=[]
    log("\n=== openHAB 4.3.2 : second runtime ecosystem ===\n")
    # virtual device
    req("PUT",f"/items/{ITEM}",adm,{"type":"Switch","name":ITEM,"label":"TenantSafe probe"})
    time.sleep(1)
    # the deputy: a rule authored by the ADMINISTRATOR that turns the item on
    rule={"uid":RULE,"name":"ts deputy","triggers":[],
          "actions":[{"id":"a1","type":"core.ItemCommandAction",
                      "configuration":{"itemName":ITEM,"command":"ON"}}],
          "conditions":[]}
    c,b=req("POST","/rules",adm,rule); log(f"  rule create -> http {c}")
    time.sleep(1.5)
    rows.append(probe("pre-removal control",mem,adm))
    log("\n  --- transition: openhab:users remove ohmember ---")
    log("  "+console("openhab:users remove ohmember").strip().splitlines()[-1] if console else "")
    time.sleep(2)
    rows.append(probe("after users remove",mem,adm))
    log("\n  --- explicit teardown: clearSessions (already-removed user) ---")
    console("openhab:users clearSessions ohmember"); time.sleep(2)
    rows.append(probe("after clearSessions",mem,adm))
    log("\n  --- control: administrator token still works? ---")
    rows.append(probe("admin token (control)",adm,adm))
    json.dump(rows,open("/tmp/p2e16_openhab.json","w"),indent=1)
    pre,post=rows[0],rows[1]
    log("\n=== VERDICT ===")
    for k in ("read","direct","deputy"):
        log(f"  {k:8s} pre={int(pre[k])} post={int(post[k])}  -> {'RESIDUAL' if pre[k] and post[k] else ('closed' if pre[k] else 'n/a (not available pre-transition)')}")
if __name__=="__main__": main()
