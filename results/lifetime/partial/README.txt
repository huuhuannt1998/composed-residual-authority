VALID measurements, truncated by an external event. Not an invalidated attempt.

attempt5_valid_to_11h.json

Sixteen probes, pre-deletion control through +11 hours, every one 1/1/1/1, no
exception on any row, on the instrument validated in ../instrument_validation/.
The run ended because Docker Desktop restarted on the host and SIGKILLed both
containers (exit 137) - the platform under test and the probe died together, at
the same instant, from outside the experiment. That is not a residue death and
not an instrument fault, so these rows stand as evidence.

What they support: the residue was verified live - socket, state read, event
stream and induced actuation all still working - at every probe through eleven
hours after the subject was deleted. The manuscript's six-hour figure is covered
by the +6h probe here, on a validated instrument, for the first time.

What they do not support: any statement about the termination events. The
automation reload, integration reload and in-UI core restart probes come after
the delay schedule and never ran.

Known fragility, and it is not fixable from inside the experiment. The residue
IS an open websocket. If the container carrying it dies the residue dies with
it, so a host-level Docker restart ends the run irrecoverably and no amount of
checkpointing would let it resume. A full 72-hour schedule needs three days
without a Docker Desktop restart on the host.


-----------------------------------------------------------------------------
attempt8_valid_to_18h.json   -- the longest clean series in the project
-----------------------------------------------------------------------------
Eighteen probes, pre-deletion control through +18 hours, every one 1/1/1/1, no
exception on any row, on the instrument validated in ../instrument_validation/.
Stopped deliberately by the PI at +18h, not by a residue death and not by an
instrument fault, so these rows stand as evidence.

This supersedes attempt 5 as the project's evidential floor. The residue was
verified live -- socket, state read, event stream and induced actuation all
still working -- eighteen hours after the subject was deleted, which is three
times the six-hour figure the manuscript claims and the second independent
clean crossing of +6h on the fixed instrument.

It says nothing about the termination events. Automation reload, integration
reload and the in-UI core restart all come after the delay schedule and did not
run. The in-UI restart result reported elsewhere comes from p1e8c
(restart_modes) and from the compressed instrument validation, both of which
measure it directly.

A resumed run is not possible and this is structural, not a missing feature:
the residue IS the open websocket, so stopping the run destroys the thing being
measured. Continuing past 18 hours would require starting a new run from zero.
