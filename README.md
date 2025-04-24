### Rewinger


Modified Airtracker to be used with Aerofly FS4 UDP capabilities.
Developed to work with Aerofly FS4
https://www.aerofly.com/community/forum/index.php?thread/24645-aerofly-fs4-udp-flight-data-recorder-and-replay-rewinger/
Features:

allowing to save a CSV with the recorded data from the flight on output_recorder
filters the initial position (0,0) from Aerofly FS4 when tracker is live

This program is an open source real-time aircraft tracker that visualizes Aerofly FS4 - (C) Copyright IPACS -
flight simulator data on an interactive map. It can be used to track flights, analyze routes,
and enhance the overall simulation experience. Key features include:

- Receives UDP data from Aerofly FS4 (C) flight simulator
- Displays the aircraft's position on a customizable map interface
- Shows real-time flight information including latitude, longitude, altitude, ground speed, heading, pitch, and roll
- Allows users to switch between different map styles
- Updates the aircraft's position and orientation in real-time
- Provides a user-friendly GUI for easy interaction

Version 25: Added a connection status label and improved error handling for UDP data reception.

:::REWINGER:::
Modifications by Emanuele Bettoni in Rewinger:
- allowing to save a CSV with the recorded data from the flight on output_recorder
- filters the initial position (0,0) from Aerofly FS4
- data can be replayed via Send_GPS_data.py output_GPS_data.csv
- added "follow aircraft" toggle
- added "arm" the recorder

Rewinger Version 2:
- cleaned the graphical interface
- added the capability to "arm" the recorder, that means: will wait until there's GPS UDP packets incoming and then starts recording
- added the "follow aircraft" toggle - without, the map does not move with the main aircraft
- Main aircraft is named "Aerofly FS4"
- corrected the known limitation that needed a live GPS stream to work with traffic

Rewinger Version 3:
- added capability to load a Google Earth *.kml file for the flight plan (e.g. from SimBrief) 

Usage:
```
python3 rewinger.py
```
if a recorder is activated, will be written into /output_recorder/
The trace will be appended so after a flight rename it with a sensible name.

Send GPS data with:
```
python3 send_GPS_data.py /path/to/file/output_GPS_data.csv GPS
```
Send Traffic data with:
```
python3 send_GPS_data.py /path/to/file/output_GPS_data.csv TRAFFIC
```