Homebridge setup-code content probe of 2026-10-04 (D2 review, N-04).

Probe experiments/p2e17c_homebridge_setupcode.py (a copy of p2e17b that, for every server-pushed event,
records only booleans: contains the bridge's HomeKit setup code, contains its setup URI, matches the generic
code and URI patterns, and for server-status events whether the pin field is non-empty and equals the code).
The code and URI are learned in memory from the first server-status event the member receives before removal
and are never written. Runner experiments/replicate_homebridge_setupcode_2026-10-04.sh: same pinned image
(homebridge/homebridge@sha256:77c685a4..., Homebridge UI 5.29.0, Homebridge 2.4.0), same setup and stimulus
as the 2026-10-03 trials; five fresh trials, all complete (rc=0); container logs NOT saved, because
Homebridge prints the setup code in them.

Result, identical in 5/5 trials (setupcode_r1..r5.json):
  delivered before removal: 4 server-status + 20 log events; after removal: 4 + 20.
  server-status events after removal: 4 of 4 carry the setup code and the setup URI (pin non-empty, equal to
  the code); the same 4 of 4 before removal.
  log events after removal: 1 of 20 carries the setup code and the setup URI (the restart prints them);
  the same 1 of 20 before removal.
  request path 200 -> 401; request on the status socket after removal unanswered and that socket closed;
  the log socket stayed open.
