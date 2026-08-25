"""TSMON — reference monitor for the TENANTSAFE calculus, Home Assistant instantiation.

Design A8, specialised to the residue the Stage 3 gate identified. The gate showed
that HA's SERVICE-CALL path is already safe (it re-resolves context.user_id by ID at
helpers/service.py:729) while every other path trusts the ActiveConnection.user object
captured at authentication time. TSMON closes the gap by applying the SAME provenance
check the service path already performs, at the two places that skip it:

  1. decorators.require_admin      -- gates fire_event, subscribe_trigger, config/*
                                      (this is the EXIT-A deputy channel)
  2. _async_get_allowed_states     -- gates get_states (the read residue)

It is deliberately the MINIMAL correct fix: no new policy, no new state, no new
configuration. It makes one path agree with another path in the same codebase.

Prototype note: uses hass.auth._store._users for a synchronous lookup because
AuthManager.async_get_user is a coroutine and require_admin wraps sync handlers.
A production fix belongs upstream where an async-safe accessor is available.
"""
import re, sys, pathlib

P = pathlib.Path("/usr/src/homeassistant/homeassistant")
GUARD = '''        # --- TSMON provenance check -------------------------------------
        _st = getattr(hass.auth, "_store", None)
        _us = getattr(_st, "_users", None) if _st is not None else None
        if user is not None and _us is not None and user.id not in _us:
            raise Unauthorized
        # --- end TSMON ---------------------------------------------------
'''

def patch_decorators():
    f = P / "components/websocket_api/decorators.py"
    s = f.read_text()
    if "TSMON provenance check" in s: return "already"
    old = ('        """Check admin and call function."""\n'
           '        user = connection.user\n\n'
           '        if user is None or not user.is_admin:\n')
    if old not in s: return "PATTERN-MISS"
    s = s.replace(old,
        '        """Check admin and call function."""\n'
        '        user = connection.user\n\n' + GUARD +
        '\n        if user is None or not user.is_admin:\n')
    f.write_text(s); return "ok"

def patch_states():
    f = P / "components/websocket_api/commands.py"
    s = f.read_text()
    if "TSMON provenance check" in s: return "already"
    old = ('    user = connection.user\n'
           '    if user.is_admin or user.permissions.access_all_entities(POLICY_READ):\n')
    if old not in s: return "PATTERN-MISS"
    s = s.replace(old,
        '    user = connection.user\n'
        '    # --- TSMON provenance check: a principal whose record no longer resolves\n'
        '    # sees nothing, regardless of the permissions cached on the stale object.\n'
        '    _st = getattr(hass.auth, "_store", None)\n'
        '    _us = getattr(_st, "_users", None) if _st is not None else None\n'
        '    if _us is not None and user.id not in _us:\n'
        '        return []\n'
        '    # --- end TSMON ---\n'
        '    if user.is_admin or user.permissions.access_all_entities(POLICY_READ):\n')
    f.write_text(s); return "ok"

print("decorators.py :", patch_decorators())
print("commands.py   :", patch_states())
