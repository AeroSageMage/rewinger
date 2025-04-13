# rewinger
Modified Airtracker to be used with Aerofly FS4 UDP capabilities.
Developed to work with Aerofly FS4
https://www.aerofly.com/community/forum/index.php?thread/24645-aerofly-fs4-udp-flight-data-recorder-and-replay-rewinger/
Features:

allowing to save a CSV with the recorded data from the flight on output_recorder
filters the initial position (0,0) from Aerofly FS4 when tracker is live
data can be replayed via
```
python3 send_GPS_data.py /path/to/file/output_GPS_data.csv
```
Known limitations:

to see the replayed data, a live Aerofly FS4 session in flight must be active (or spoofed via UDP packet)
need to remove the garish warning stripe around the log data button
Airplane info must be entered manually in the first line of the CSV file (see example) for traffic to show the ICAO and flight number

Usage:

```
python3 rewinger.py
```