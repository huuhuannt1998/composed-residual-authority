Instrument validation for the 72-hour persistence probe. NOT a result.

The failure that invalidated four attempts depends on the NUMBER of probes, not
on elapsed time: each probe leaves a few frames unread on a socket carrying a
live subscribe_events subscription, and the client stalls once its receive queue
fills (see ../invalidated/README.txt, fault 2). So the whole schedule can be
exercised in minutes by compressing the sleeps, and that compressed run puts the
instrument through exactly the failure path that killed the real ones.

SCHED_SCALE compresses every sleep. 1.0 is the real 72-hour schedule and is the
default; any other value stamps the rows file SMOKE_TEST_not_a_result so a
compressed run can never be mistaken for evidence.

Result of the compressed run, 30 probes end to end:

  all delay probes, pre-deletion through +72 hours   1/1/1/1
  after automation reload                            1/1/1/1
  after integration reload                           1/1/1/1
  after in-UI core restart                           0/0/0/0  close_code=1000

Attempt 4 died at probe 11 and attempt 1 at probe 7, so 30 clean probes clears
both by a wide margin.

The last row is the reason this validation was worth running twice. It used to
read "failed" with no measurement at all: Home Assistant tears the socket down
while servicing its own restart, so the service call never returns a result
frame, and waiting for one turned a real measurement into a timeout. The probe
now expects no reply and waits for the platform to return. The row that comes
back carries close_code=1000, a clean platform-initiated close - which is the
in-UI restart deliberately ending the residue, not a transport failure.
