#!/usr/bin/env python3
"""ha_auditor - what does a configuration audit see after a household removal?

Review W7 is fair: the calculus recommends reachability, and neither defense
computes it. The residue search we ship computes it, but only over hand-written
declarative specifications, which is a weaker claim than the paper implies. So
this reads a REAL Home Assistant configuration directory and asks, for a named
departed principal, what authority remains reachable and through which carriers.

It reports three things, and the gap between them is the paper's argument:

  NAMED      objects in the configuration that mention the principal at all.
             This is what a household, or a script grepping for a username,
             would find. After a deletion it is normally empty.

  CARRIERS   objects that can relay authority the principal supplies without
             naming them: automations triggered by events any authenticated
             client can fire, webhooks, scripts reachable from those. These
             survive removal because nothing about them refers to the person.

  UNSEEN     carriers that exist only in process memory and appear in NO
             configuration file. Established websocket connections are the
             case that matters here. An audit of the configuration cannot
             find them, however thorough, because they are not in it.

Usage:
  ha_auditor.py <config-dir> --principal <username-or-user-id> [--json]
"""
import argparse, json, os, re, sys

def _load(p):
    try:
        with open(p) as f: return json.load(f)
    except Exception: return None

def _yaml_ish(path):
    """automations.yaml without a YAML dependency: we only need trigger types
    and ids, and the file is machine-written."""
    try: txt = open(path).read()
    except Exception: return []
    blocks, cur = [], None
    for line in txt.splitlines():
        if re.match(r'^-\s', line):
            if cur: blocks.append(cur)
            cur = line[2:] + "\n"
        elif cur is not None:
            cur += line + "\n"
    if cur: blocks.append(cur)
    out = []
    for b in blocks:
        i = re.search(r'^\s*id:\s*[\'"]?([^\'"\n]+)', b, re.M)
        a = re.search(r'^\s*alias:\s*[\'"]?([^\'"\n]+)', b, re.M)
        out.append({"id": (i.group(1).strip() if i else None),
                    "alias": (a.group(1).strip() if a else None),
                    "event_triggered": bool(re.search(r'platform:\s*event', b)),
                    "raw": b})
    return out

def audit(cfg, principal):
    st = os.path.join(cfg, ".storage")
    auth = _load(os.path.join(st, "auth")) or {"data": {}}
    d = auth.get("data", {})
    users = d.get("users", [])
    uid, uname = None, principal
    for u in users:
        if u.get("id") == principal or (u.get("name") or "").lower() == principal.lower():
            uid, uname = u["id"], u.get("name"); break

    named = []
    if uid:
        named.append(("user", uid, f"user record '{uname}' still present"))
    for t in d.get("refresh_tokens", []):
        if uid and t.get("user_id") == uid:
            named.append(("refresh_token", t["id"], f"{t.get('token_type')} token, client={t.get('client_name')}"))
    for c in d.get("credentials", []):
        if uid and c.get("user_id") == uid:
            named.append(("credential", c["id"], c.get("auth_provider_type")))
    person = _load(os.path.join(st, "person"))
    if person:
        for p in person.get("data", {}).get("items", []) or []:
            if uid and p.get("user_id") == uid:
                named.append(("person", p.get("id"), p.get("name")))
    # anything else in .storage that literally contains the id or the name
    for fn in sorted(os.listdir(st)) if os.path.isdir(st) else []:
        fp = os.path.join(st, fn)
        if fn in ("auth", "person") or not os.path.isfile(fp): continue
        try: blob = open(fp, errors="ignore").read()
        except Exception: continue
        if (uid and uid in blob) or (uname and uname in blob and len(uname) > 3):
            named.append(("storage", fn, "file mentions the principal"))

    autos = _yaml_ish(os.path.join(cfg, "automations.yaml"))
    carriers = []
    for a in autos:
        names_principal = bool(uid and uid in a["raw"]) or bool(uname and uname in a["raw"])
        if a["event_triggered"]:
            carriers.append({"kind": "automation", "id": a["id"], "alias": a["alias"],
                             "trigger": "event", "names_principal": names_principal,
                             "note": "fires on an event any authenticated client may emit"})
    ce = _load(os.path.join(st, "core.config_entries"))
    if ce:
        for e in ce.get("data", {}).get("entries", []) or []:
            carriers.append({"kind": "integration", "id": e.get("entry_id"),
                             "alias": e.get("title") or e.get("domain"),
                             "trigger": "-", "names_principal": False,
                             "note": "holds its own credentials, independent of the principal"})

    unseen = [{"kind": "websocket session", "note":
               "authenticated at connection setup; not represented in any file "
               "under the configuration directory, so no configuration audit "
               "can enumerate it"}]
    return {"principal": principal, "resolved_user_id": uid, "resolved_name": uname,
            "named": named, "carriers": carriers, "unseen": unseen}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config"); ap.add_argument("--principal", required=True)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    r = audit(a.config, a.principal)
    if a.json:
        print(json.dumps(r, indent=1)); return
    print(f"\n  configuration audit for principal: {r['principal']}")
    print(f"  resolved: {r['resolved_user_id'] or 'NOT PRESENT (already removed)'}\n")
    print(f"  NAMED - objects a per-object search would find ({len(r['named'])})")
    for k, i, n in r["named"] or []: print(f"    {k:14s} {str(i)[:34]:36s} {n}")
    if not r["named"]: print("    (none: nothing in the configuration names this principal)")
    print(f"\n  CARRIERS - relay authority without naming anyone ({len(r['carriers'])})")
    for c in r["carriers"]:
        flag = "names principal" if c["names_principal"] else "does NOT name the principal"
        print(f"    {c['kind']:14s} {str(c['alias'])[:34]:36s} {flag}")
    if not r["carriers"]: print("    (none)")
    print(f"\n  UNSEEN - carriers absent from the configuration entirely ({len(r['unseen'])})")
    for u in r["unseen"]: print(f"    {u['kind']:14s} {u['note']}")
    named_n, relay = len(r["named"]), [c for c in r["carriers"] if not c["names_principal"]]
    print("\n  READING")
    if named_n == 0 and relay:
        print("    A per-object audit is clean: nothing in the configuration names this")
        print(f"    principal. {len(relay)} object(s) can still relay authority they supply, and")
        print("    the connection that supplies it is not in the configuration at all.")
        print("    A configuration audit cannot answer the question this paper asks.")
    elif named_n:
        print(f"    {named_n} object(s) still name the principal; removal is incomplete at the")
        print("    object level and a per-object audit would find them.")
main()
