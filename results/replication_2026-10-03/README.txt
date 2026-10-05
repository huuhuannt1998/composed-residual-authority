Replications of 2026-10-03 (D1 review: F-03 single-run arms; F-08 Homebridge probe).

Runner: experiments/replicate_2026-10-03.sh (streams A, B, R) and
        experiments/replicate_homebridge_2026-10-03.sh; new probe experiments/p2e17b_homebridge_delivered.py.
Every Home Assistant arm calls its ORIGINAL script unchanged (p1e21_auditor_rerun.py, p0e3_capability_matrix.py,
p1e7b_sessions.py, p1e18_thirdparty_carrier.py, p1e12_regression.py) on a fresh homeassistant/home-assistant:2026.8.3
container (image sha256:14931c6b...) per repetition; defenses applied with the same patch files as run_all.sh.
Homebridge: homebridge/homebridge@sha256:77c685a4... (Docker release 2026-09-02; Homebridge UI 5.29.0; Homebridge 2.4.0),
fresh container and volume per trial, non-admin member as subject.

n = 5 per arm/condition (Homebridge: 5 trials, plus 2 pilots reported separately: pilot1 has no baseline because the
restart stimulus was sent without a JSON body (HTTP 415); pilot21 ran before payload-key recording was added and gave
the same outcome as the five trials).

Outcome: every Home Assistant arm reproduced its original single run in 5 of 5 repetitions (summary.json). Homebridge:
request path HTTP 200 -> 401 in 5/5; the member's socket subscribed before removal kept receiving the same number of
server-status (4) and log (20) events after removal as before (delivered-event baseline present in every trial); a
request-response message sent after removal was refused and that socket closed, 5/5.

Files: manifest_*.log (timestamps, rc, image ids), per-run outputs, summary.json (python3 summarize.py),
SHA256SUMS (sha256 of every file here except itself, and of the runner and probe scripts).
No earlier result file was modified.
