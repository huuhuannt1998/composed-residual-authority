"""P1 EXPERIMENT 11 (microbenchmark, corrected).

Timing each individual lookup with perf_counter_ns() measures the timer as much
as the lookup: two clock reads cost tens of nanoseconds and the operation itself
is a dict get. Two estimators are reported and the difference between them IS
the timer overhead, so neither is presented as the other.

  per-op    : clock around each lookup. Upper bound; includes timer cost.
  amortized : clock around a batch of K lookups, divided by K. The real cost.

A no-op batch of the same shape calibrates loop overhead and is subtracted.
"""
import statistics as stat, time, json
def build():
    p={f"light.l{i}":{"read":True,"control":i%2==0} for i in range(500)}
    p["input_boolean.ts_probe"]={"read":True,"control":True}
    return p,list(p)
def per_op(iters=1_000_000):
    pol,keys=build(); nk=len(keys); s=[]
    for i in range(iters):
        k=keys[i%nk]; t=time.perf_counter_ns()
        pol.get(k,{}).get("control",False)
        s.append(time.perf_counter_ns()-t)
    s.sort(); q=lambda x: s[min(len(s)-1,int(len(s)*x))]
    return dict(median_ns=q(.5),p95_ns=q(.95),p99_ns=q(.99),stdev_ns=round(stat.pstdev(s[:200_000]),1))
def amortized(iters=1_000_000,batches=30):
    pol,keys=build(); nk=len(keys); K=iters//batches; per=[]
    for b in range(batches):
        t=time.perf_counter_ns()
        for i in range(K): pol.get(keys[i%nk],{}).get("control",False)
        real=time.perf_counter_ns()-t
        t=time.perf_counter_ns()
        for i in range(K): keys[i%nk]                     # same loop, no lookup
        noop=time.perf_counter_ns()-t
        per.append((real-noop)/K)
    per.sort(); q=lambda x: per[min(len(per)-1,int(len(per)*x))]
    return dict(batches=batches,batch_size=K,median_ns=round(q(.5),1),p95_ns=round(q(.95),1),
                p99_ns=round(q(.99),1),stdev_ns=round(stat.pstdev(per),2),
                throughput_per_s=int(1e9/q(.5)))
if __name__=="__main__":
    a=per_op(); b=amortized()
    print(f"  per-op    (incl. timer): median {a['median_ns']} ns  p95 {a['p95_ns']}  p99 {a['p99_ns']}  sd {a['stdev_ns']}")
    print(f"  amortized (loop-calibrated): median {b['median_ns']} ns  p95 {b['p95_ns']}  p99 {b['p99_ns']}  sd {b['stdev_ns']}")
    print(f"  batches {b['batches']} x {b['batch_size']:,} = {b['batches']*b['batch_size']:,} lookups; {b['throughput_per_s']:,}/s")
    print(f"  timer overhead implied: {a['median_ns']-b['median_ns']:.1f} ns per measured op")
    json.dump({"per_op":a,"amortized":b},open("/tmp/p1e11_micro.json","w"),indent=1)
