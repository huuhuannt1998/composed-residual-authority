"""P1 EXPERIMENT 11 - corrected end-to-end performance evaluation.

The earlier attempt was confounded: patch and revert each required a container
restart, so "condition" and "restart" moved together and any restart effect was
indistinguishable from a defense effect.

THE FIX. Three instances run SIMULTANEOUSLY on separate ports - baseline,
Defense A, Defense B - each brought up with the SAME number of restarts. Nothing
is patched during measurement. Arms are then measured in ROTATION within each
run, and the arm order is permuted per run, so drift in host load is spread
across arms instead of aligning with one.

Reported: p50, p95, p99, throughput, and a t-based 95% CI over the per-run
medians of 5 independent runs. Differences smaller than the CI overlap are NOT
claimed.
"""
import asyncio, json, statistics as stat, sys, time
import aiohttp, websockets
ARMS=[("baseline","8141"),("defense A","8142"),("defense B","8143")]
OWNER=("tsowner","Owner-Passw0rd-123"); EID="input_boolean.ts_probe"
OPS=["state read","event fire","service call","ws round trip"]
RUNS=5; N=2500; WARM=300
log=lambda m: print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)

# ---------------------------------------------------------------- microbenchmark
def microbench(iters=1_000_000):
    """The authorization check Home Assistant performs per operation is a nested
    dict lookup on the compiled policy. Measure that shape directly."""
    policy={f"light.l{i}":{"read":True,"control":i%2==0} for i in range(500)}
    policy["input_boolean.ts_probe"]={"read":True,"control":True}
    keys=list(policy); nk=len(keys)
    samples=[]; t0=time.perf_counter_ns()
    for i in range(iters):
        k=keys[i%nk]
        s=time.perf_counter_ns()
        _=policy.get(k,{}).get("control",False)
        samples.append(time.perf_counter_ns()-s)
    total=(time.perf_counter_ns()-t0)/1e9
    samples.sort()
    q=lambda p: samples[min(len(samples)-1,int(len(samples)*p))]
    return dict(iterations=iters,median_ns=q(.5),p95_ns=q(.95),p99_ns=q(.99),
                stdev_ns=stat.pstdev(samples[:200000]),wall_s=round(total,2),
                throughput_per_s=int(iters/total))

# ---------------------------------------------------------------- harness
def base(p): return f"http://localhost:{p}"
async def tokc(s,p,c):
    async with s.post(f"{base(p)}/auth/token",data={"grant_type":"authorization_code","code":c,"client_id":f"{base(p)}/"}) as r: return await r.json()
async def onboard(s,p):
    async with s.post(f"{base(p)}/api/onboarding/users",json={"client_id":f"{base(p)}/","name":"TS Owner",
        "username":OWNER[0],"password":OWNER[1],"language":"en"}) as r:
        if r.status!=200: return None
        code=(await r.json())["auth_code"]
    t=(await tokc(s,p,code))["access_token"]
    for stp in ("core_config","analytics"):
        async with s.post(f"{base(p)}/api/onboarding/{stp}",headers={"Authorization":f"Bearer {t}"}) as r: await r.text()
    return t
async def login(s,p):
    async with s.post(f"{base(p)}/auth/login_flow",json={"client_id":f"{base(p)}/","handler":["homeassistant",None],"redirect_uri":f"{base(p)}/","type":"authorize"}) as r:
        f=(await r.json())["flow_id"]
    async with s.post(f"{base(p)}/auth/login_flow/{f}",json={"client_id":f"{base(p)}/","username":OWNER[0],"password":OWNER[1]}) as r:
        j=await r.json()
        if "result" not in j: return None
    return (await tokc(s,p,j["result"]))["access_token"]
class C:
    def __init__(s,ws): s.ws,s.id=ws,0
    async def cmd(s,**kw):
        s.id+=1; await s.ws.send(json.dumps({"id":s.id,**kw}))
        want = "pong" if kw.get("type")=="ping" else "result"
        while True:
            m=json.loads(await asyncio.wait_for(s.ws.recv(),timeout=20))
            if m.get("id")==s.id and m["type"]==want: return m
async def conn(p,t):
    ws=await websockets.connect(f"ws://localhost:{p}/api/websocket",max_size=None); await ws.recv()
    await ws.send(json.dumps({"type":"auth","access_token":t})); m=json.loads(await ws.recv())
    return C(ws) if m["type"]=="auth_ok" else None
async def timed(c,op):
    t=time.perf_counter_ns()
    if op=="state read":     await c.cmd(type="get_states")
    elif op=="event fire":   await c.cmd(type="fire_event",event_type="bench_ping")
    elif op=="service call": await c.cmd(type="call_service",domain="input_boolean",service="toggle",target={"entity_id":EID})
    else:                    await c.cmd(type="ping")
    return (time.perf_counter_ns()-t)/1e6      # ms

def ci95(xs):
    if len(xs)<2: return (float('nan'),float('nan'))
    m=stat.mean(xs); sd=stat.stdev(xs); t=2.776 if len(xs)==5 else 2.262
    h=t*sd/(len(xs)**0.5); return (m-h,m+h)

async def main():
    log("microbenchmark: 1,000,000 authorization-check lookups")
    mb=microbench()
    log(f"  median {mb['median_ns']} ns  p95 {mb['p95_ns']} ns  p99 {mb['p99_ns']} ns  "
        f"sd {mb['stdev_ns']:.1f} ns  {mb['throughput_per_s']:,}/s over {mb['wall_s']}s")
    async with aiohttp.ClientSession() as s:
        conns={}
        for name,p in ARMS:
            t=await onboard(s,p) or await login(s,p)
            c=await conn(p,t); conns[name]=c
            try: await c.cmd(type="input_boolean/create",name="ts probe")
            except Exception: pass
        await asyncio.sleep(1.5)
        log(f"warm-up: {WARM} ops per arm per operation")
        for name,_ in ARMS:
            for op in OPS:
                for _ in range(WARM//len(OPS)): await timed(conns[name],op)
        data={n:{o:[] for o in OPS} for n,_ in ARMS}     # per-run medians
        raw ={n:{o:[] for o in OPS} for n,_ in ARMS}
        for run in range(RUNS):
            order=ARMS[run%len(ARMS):]+ARMS[:run%len(ARMS)]   # permute arm order per run
            log(f"run {run+1}/{RUNS}  arm order: {[n for n,_ in order]}")
            for op in OPS:
                for name,_ in order:
                    xs=[await timed(conns[name],op) for _ in range(N)]
                    raw[name][op].extend(xs)
                    data[name][op].append(stat.median(xs))
        out={"microbenchmark":mb,"runs":RUNS,"ops_per_arm_per_run":N*len(OPS),"arms":{}}
        log("")
        log("=== END-TO-END LATENCY (ms) ===")
        log(f"  {'operation':15s} {'arm':11s} {'p50':>8s} {'p95':>8s} {'p99':>8s} {'thru/s':>9s}   95% CI of per-run medians")
        for op in OPS:
            for name,_ in ARMS:
                xs=sorted(raw[name][op]); q=lambda p: xs[min(len(xs)-1,int(len(xs)*p))]
                lo,hi=ci95(data[name][op])
                out["arms"].setdefault(name,{})[op]=dict(p50=q(.5),p95=q(.95),p99=q(.99),
                    n=len(xs),run_medians=data[name][op],ci95=[lo,hi],throughput=1000.0/max(1e-9,stat.mean(xs)))
                log(f"  {op:15s} {name:11s} {q(.5):8.3f} {q(.95):8.3f} {q(.99):8.3f} {1000.0/stat.mean(xs):9.1f}   [{lo:.3f}, {hi:.3f}]")
            log("")
        # overlap test: is any defense distinguishable from baseline?
        log("=== IS ANY DIFFERENCE LARGER THAN NOISE? ===")
        for op in OPS:
            b=out["arms"]["baseline"][op]["ci95"]
            for name in ("defense A","defense B"):
                d=out["arms"][name][op]["ci95"]
                overlap = not (d[0]>b[1] or d[1]<b[0])
                log(f"  {op:15s} {name:11s} -> {'CI overlaps baseline; no difference claimed' if overlap else 'CI SEPARATED from baseline'}")
        json.dump(out,open("/tmp/p1e11_bench.json","w"),indent=1)
        log("\nwritten /tmp/p1e11_bench.json")
asyncio.run(main())
