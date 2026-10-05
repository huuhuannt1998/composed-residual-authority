attempt9_complete_72h.json -- the complete schedule, first time it has finished.

Thirty-one rows. Twenty-seven delay probes from the pre-deletion control through
+72 hours, every one 1/1/1/1 on all four channels, with no exception on any row.
Then the termination events, measured inside the same continuous series rather
than inferred across separate runs:

  after automation reload     1/1/1/1
  after integration reload    1/1/1/1
  after in-UI core restart    0/0/0/0   close_code=1000
  after container restart     0/0/0/0

The close code is the point. 1000 is a clean, deliberate close initiated by the
platform, not a transport failure, so the in-interface "Restart Home Assistant"
is observed ENDING the residue rather than the connection merely being found
dead afterwards. Every earlier zero in this project's lifetime work arrived as
1006 or 1011, which is exactly why four attempts had to be discarded as
instrument faults. A 1000 here is the difference between a measurement and an
absence of one.

One qualification, recorded rather than smoothed over. After issuing the
restart, the observer could not re-establish its own connection within the two
minutes allowed, so the stream and actuation columns on that row are not
independently confirmed. The socket and read columns are measured directly on
the subject connection and are what the row rests on; with a clean 1000 close
the residue is ended regardless of what the observer could see.

Nine attempts. Four were invalidated by two instrument faults, both since
identified and fixed (see ../invalidated/README.txt). Two were valid but cut
short and are retained (see ../partial/). This is the ninth and it ran the
schedule end to end.
