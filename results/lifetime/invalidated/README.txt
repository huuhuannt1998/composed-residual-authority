Four invalidated attempts at the long persistence schedule, retained
deliberately. TWO separate instrument faults, both now identified and both
closed. Neither was a property of the residue.

-----------------------------------------------------------------------------
FAULT 1 - the platform closes a client that does not answer its heartbeat
-----------------------------------------------------------------------------
attempt2_idle_transport_1006.json          client keepalive OFF, died +2h, 1006
attempt3_innetwork_no_client_pong.json     client keepalive OFF, died +1h, 1006

Home Assistant sets, in components/websocket_api/http.py:

    self._wsock = web.WebSocketResponse(heartbeat=55, decode_text=False)

It pings every 55 seconds and closes a connection that does not pong. Disabling
the measuring client's keepalive stopped it answering, so the platform closed
the connection and the probe scored a residue death that had not happened.
Attempt 3 ran from inside the docker network with no host port forwarding in the
path and died even earlier, which ruled the forwarder out.

Source-confirmed. The client keepalive stays ON.

-----------------------------------------------------------------------------
FAULT 2 - the measuring client stops reading, so it stops processing PONGs
-----------------------------------------------------------------------------
attempt1_client_keepalive_1011.json        keepalive ON,  died +2h (probe 7)
attempt4_maxqueue_backpressure_1011.json   keepalive ON,  died +5-6h (probe 11)

Both died with the client sending 1011 "keepalive ping timeout" and then reading
1006. Home Assistant logged nothing and was serving normally afterwards.

The subject socket holds a live subscribe_events subscription, so the platform
pushes at it continuously, but the old probe only ever called recv() during a
probe - up to an hour apart. websockets 17.1 defaults to max_queue=16. Once
sixteen messages are buffered unread the library applies backpressure and stops
reading the transport, and a transport that is not being read does not process
incoming PONGs either. The client's own keepalive then times out and it closes
the connection it is measuring. Each probe leaves a couple of frames unread,
which is why the death arrives after roughly a dozen probes rather than at a
fixed wall-clock time, and why it moved from probe 7 to probe 11 when the ping
timeout was widened - widening the timeout delayed the symptom, not the cause.

Confirmed directly, not inferred: maxqueue_backpressure_test.py opens two
sockets that are identical but for draining, both subscribed, both with the
library keepalive on, and pushes 60 events past the 16-slot queue.

    A (undrained)  close_code=1006  reason=''     dead at ~40s
    B (drained)    close_code=None                alive at +90s

Fixed in class C of the probe: exactly one coroutine calls recv(), always, and
it demultiplexes command results to waiting futures and events to a bounded log.
Nothing accumulates and backpressure is never reached. max_queue is also raised
to 512 as a second line of defence behind that reader. A client that subscribes
to events now actually reads them, which is what a real client does anyway.

-----------------------------------------------------------------------------
CORRECTION to the previous version of this file
-----------------------------------------------------------------------------
The previous text said "the original instrument (ping_interval=20) was correct
and its six-hour result is not in doubt", and attributed all three deaths then
in hand to fault 1. That was wrong on both counts. Attempt 1 WAS the original
instrument, it had the keepalive on, and it died at +2h of fault 2. Fault 1
explains attempts 2 and 3 only. The earlier campaign's unexplained 0/0/0/0 at
+6h, which that text offered fault 1 to explain, is better explained by fault 2:
the same undrained subscription, the same probe cadence, the same signature.

Consequently the earlier campaign's six-hour figure is NOT independently
corroborated by these runs, and no claim rests on it until a clean run lands.
The longest verified-clean series so far is attempt 4's ten probes, which read
1/1/1/1 through +5 hours before fault 2 ended it.

-----------------------------------------------------------------------------
WHAT SURVIVES AS A FINDING
-----------------------------------------------------------------------------
Fault 1 is an instrument note and also a result: the residue is not
fire-and-forget. It requires a client that stays connected AND answers the
platform's heartbeat, so a departed principal whose laptop closes or phone
sleeps loses it within about a minute. That qualifier is in the manuscript.

Fault 2 is an instrument fault only and carries no claim about the platform.
