"""DEFENSE A - terminate sessions on user removal.

Defense B (continuous principal re-resolution, models/tsmon_patch.py) closes the
paths that consult the auth store, but the capability matrix shows it leaves the
EVENT-FORWARDING path open: _forward_events_check_permissions receives a User
object and no hass handle, so it cannot re-resolve, and both new and pre-existing
subscriptions keep delivering to a deleted principal.

Defense A attacks the root cause instead. Home Assistant already terminates
sessions correctly on DEACTIVATION, by routing each refresh token through
AuthManager.async_remove_refresh_token, which fires the revoke callbacks that
cancel the live WebSocket. Removal bypasses that path. Making removal do what
deactivation already does closes every channel at once, because the socket ceases
to exist.
"""
import pathlib
P = pathlib.Path("/usr/src/homeassistant/homeassistant")
f = P / "auth/__init__.py"
s = f.read_text()
if "TSMON Defense A" in s:
    print("already applied")
else:
    old = ('    async def async_remove_user(self, user: models.User) -> None:\n'
           '        """Remove a user."""\n'
           '        tasks = [\n')
    if old not in s:
        print("PATTERN-MISS"); raise SystemExit(1)
    new = ('    async def async_remove_user(self, user: models.User) -> None:\n'
           '        """Remove a user."""\n'
           '        # --- TSMON Defense A -------------------------------------------\n'
           '        # Route tokens through the manager so the revoke callbacks fire and\n'
           '        # any live WebSocket is cancelled, matching async_deactivate_user.\n'
           '        for _rt in list(user.refresh_tokens.values()):\n'
           '            self.async_remove_refresh_token(_rt)\n'
           '        # --- end TSMON Defense A ---------------------------------------\n'
           '        tasks = [\n')
    f.write_text(s.replace(old, new))
    print("Defense A applied to async_remove_user")
