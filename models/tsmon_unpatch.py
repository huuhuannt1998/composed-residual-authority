import pathlib, re
P = pathlib.Path("/usr/src/homeassistant/homeassistant")
def strip(f, start, end):
    s = f.read_text()
    if "TSMON" not in s: return "already-clean"
    s = re.sub(start, "", s, flags=re.S)
    f.write_text(s); return "reverted"
d = P/"components/websocket_api/decorators.py"
print("decorators:", strip(d, r"\n?        # --- TSMON provenance check.*?# --- end TSMON ---------------------------------------------------\n", None))
c = P/"components/websocket_api/commands.py"
print("commands  :", strip(c, r"\n?    # --- TSMON provenance check.*?# --- end TSMON ---\n", None))
