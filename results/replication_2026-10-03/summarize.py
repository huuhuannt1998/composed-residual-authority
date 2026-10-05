"""Summarize the 2026-10-03 replications (D1 review, F-03 and F-08) from the result files in
this directory, compare each arm with its original single run, and write summary.json.
Read only on every other file; run after all streams finish:  python3 summarize.py"""
import glob, json, os, re
H = os.path.dirname(os.path.abspath(__file__))
LOGS = os.path.join(H, "..", "run-logs")
out = {}

# configuration auditor (p1e21): before/after counts and the three probe points
aud = []
for f in sorted(glob.glob(os.path.join(H, "auditor_r*_probe.log"))):
    t = open(f).read()
    a = {k: (int(n), int(c), int(u)) for k, n, c, u in re.findall(
        r"AUDIT (before|after|after_by_name)\s+principal=\S+ resolved=\S+ named=(\d+) carriers=(\d+) unseen=(\d+)", t)}
    p = re.findall(r"(pre-deletion control|after deletion, before audit|after deletion, after audit)\s+(\d/\d/\d/\d)", t)
    aud.append({"file": os.path.basename(f), "named": [a["before"][0], a["after"][0], a["after_by_name"][0]],
                "carriers": [a[k][1] for k in ("before", "after", "after_by_name")],
                "unseen": [a[k][2] for k in ("before", "after", "after_by_name")], "probe": [v for _, v in p]})
out["auditor"] = {"runs": aud, "original": "p1e21_auditor_rerun_2026-10-02_probe.log: named 3/0/0, carriers 8, unseen 1, probe 1/1/1/1 x3",
                  "all_match_original": all(r["named"] == [3, 0, 0] and r["carriers"] == [8, 8, 8] and r["unseen"] == [1, 1, 1]
                                            and r["probe"] == ["1/1/1/1"] * 3 for r in aud)}

# capability matrix (p0e3)
def cap_orig(fn):
    t = open(os.path.join(LOGS, fn)).read()
    return sorted(re.search(r"residual capabilities:\s*\d+\s+\[(.*)\]", t).group(1).replace("'", "").split(", ")) if "[]" not in t.split("residual capabilities:")[1].split("\n")[0] else []
cap = {}
for arm, orig in (("baseline", "capability_base.log"), ("defenseB", "capability_defB.log"), ("defenseA", "capability_defA.log")):
    rows = []
    for f in sorted(glob.glob(os.path.join(H, f"capability_{arm}_r*.json"))):
        d = json.load(open(f))
        rows.append({"file": os.path.basename(f), "held_pre": sum(d["pre"].values()), "probed": len(d["pre"]),
                     "residual": sorted(d["residual"])})
    o = cap_orig(orig)
    cap[arm] = {"runs": rows, "original_residual": o, "all_match_original": all(r["residual"] == o for r in rows)}
out["capability"] = cap

# regression suite (p1e12)
reg = {}
for arm, orig in (("base", "regression_base.log"), ("defB", "regression_defB.log"), ("defA", "regression_defA.log")):
    rows = []
    for f in sorted(glob.glob(os.path.join(H, f"regression_{arm}_r*.json"))):
        d = json.load(open(f))
        rows.append({"file": os.path.basename(f), "tests": len(d["tests"]), "passed": d["passed"],
                     "security_regressions": d["security_regressions"], "functional_regressions": d["functional_regressions"],
                     "outcomes": [t["kind"] for t in d["tests"]]})
    t = open(os.path.join(LOGS, orig)).read()
    o = (int(re.search(r"(\d+) passed", t).group(1)), int(re.search(r"(\d+) security regressions", t).group(1)),
         int(re.search(r"(\d+) functional regressions", t).group(1)))
    reg[arm] = {"runs": rows, "original_passed_sec_func": o,
                "all_match_original": all((r["passed"], r["security_regressions"], r["functional_regressions"]) == o for r in rows)}
out["regression"] = reg

# session-condition arms (p1e7b) and third-party token arm (p1e18)
def ses_rows(text):
    return [re.sub(r"\(killed=.*?\)\)", "(killed=...)", l.strip()) for l in text.splitlines() if re.match(r"\s+A\d", l)]
def ses_cells(text):
    return [re.findall(r"(\d/\d/\d)", l)[-2:] for l in text.splitlines() if re.match(r"\s+A\d", l)]
o_ses = ses_cells(open(os.path.join(LOGS, "sessions.log")).read())
ses = [{"file": os.path.basename(f), "cells": ses_cells(open(f).read())} for f in sorted(glob.glob(os.path.join(H, "sessions_r*.log")))]
out["sessions"] = {"runs": ses, "original_cells": o_ses, "all_match_original": all(r["cells"] == o_ses for r in ses)}
def tp(text):
    return (re.search(r"BEFORE removal\s+(HTTP \d+), entity=(\w+)", text).groups(),
            re.search(r"AFTER removal\s+(HTTP \d+), entity=(\w+)", text).groups(),
            re.search(r"still reads\s+(\w+)", text).group(1))
o_tp = tp(open(os.path.join(LOGS, "thirdparty_carrier.log")).read())
tpr = [{"file": os.path.basename(f), "result": tp(open(f).read())} for f in sorted(glob.glob(os.path.join(H, "thirdparty_r*.log")))]
out["thirdparty"] = {"runs": tpr, "original": o_tp, "all_match_original": all(r["result"] == o_tp for r in tpr)}

# Homebridge delivered-event probe (p2e17b), trials r1-r5 (pilots reported separately)
hb = []
for f in sorted(glob.glob(os.path.join(H, "homebridge_r*.json"))):
    d = json.load(open(f))
    hb.append({"file": os.path.basename(f), **{k: d[k] for k in ("pre_delivered", "post_delivered", "pre_request_path_http",
               "post_request_path_http", "pre_request_response_ack", "post_request_response_ack", "post_alive_after_stimulus",
               "post_alive_after_incoming", "verdict")}, "post_status_payload_keys": d.get("post_status_payload_keys")})
pil = [{"file": os.path.basename(f), "pre_stimulus_http": json.load(open(f)).get("pre_stimulus_http"),
        "verdict": json.load(open(f))["verdict"]} for f in sorted(glob.glob(os.path.join(H, "homebridge_pilot*.json")))]
out["homebridge"] = {"trials": hb, "pilots": pil,
                     "original": "run-logs/homebridge_probe.log: request path 200 -> 401; socket 'events' 1 before (the connect callback) and 0 after; no delivered-event baseline"}
json.dump(out, open(os.path.join(H, "summary.json"), "w"), indent=1)
print(json.dumps({k: (v.get("all_match_original") if isinstance(v, dict) and "all_match_original" in v else
                      {a: x.get("all_match_original") for a, x in v.items()} if k in ("capability", "regression") else "see file")
                  for k, v in out.items()}, indent=1))
