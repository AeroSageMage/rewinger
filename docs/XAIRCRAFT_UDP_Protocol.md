# XAIRCRAFT UDP Protocol Documentation

> **Note**: This documentation is a work in progress and is based on the implementation in the rewinger/SkyBridge project. The protocol is subject to change as the project evolves.

## Overview

This documentation describes both the ForeFlight UDP protocol and its extension through the XAIRCRAFT protocol. The ForeFlight UDP protocol is a standard protocol used by flight simulators to transmit aircraft position and attitude data. The XAIRCRAFT protocol is a custom extension developed for the rewinger/SkyBridge project to provide additional aircraft metadata information.

## ForeFlight UDP Protocol Messages

The following message types are part of the standard ForeFlight UDP protocol:

### 1. XTRAFFIC Message
Used to transmit aircraft traffic information.

**Format:**
```
XTRAFFIC<simulator_name>,<icao_address>,<latitude>,<longitude>,<altitude_ft>,<vertical_speed_ft/min>,<airborne_flag>,<heading_true>,<velocity_knots>,<callsign>
```

**Fields:**
- `simulator_name`: Name of the flight simulator
- `icao_address`: ICAO 24-bit address of the aircraft
- `latitude`: Aircraft latitude in decimal degrees
- `longitude`: Aircraft longitude in decimal degrees
- `altitude_ft`: Aircraft altitude in feet
- `vertical_speed_ft/min`: Vertical speed in feet per minute
- `airborne_flag`: 1 if aircraft is airborne, 0 if on ground
- `heading_true`: True heading in degrees
- `velocity_knots`: Ground speed in knots
- `callsign`: Aircraft callsign

### 2. XGPS Message
Used to transmit GPS position data.

**Format:**
```
XGPS<simulator_name>,<longitude>,<latitude>,<altitude_msl>,<track_true_north>,<groundspeed_m/s>
```

**Fields:**
- `simulator_name`: Name of the flight simulator
- `longitude`: Aircraft longitude in decimal degrees
- `latitude`: Aircraft latitude in decimal degrees
- `altitude_msl`: Altitude above mean sea level in meters
- `track_true_north`: Track angle relative to true north in degrees
- `groundspeed_m/s`: Ground speed in meters per second

### 3. XATT Message
Used to transmit aircraft attitude data.

**Format:**
```
XATT<simulator_name>,<heading>,<pitch>,<roll>
```

**Fields:**
- `simulator_name`: Name of the flight simulator
- `heading`: Aircraft heading in degrees
- `pitch`: Aircraft pitch angle in degrees
- `roll`: Aircraft roll angle in degrees

## Custom XAIRCRAFT Extension

The XAIRCRAFT message is a custom extension developed for the rewinger/SkyBridge project to provide additional aircraft metadata information.

### XAIRCRAFT Message
Used to transmit aircraft metadata information.

**Format:**
```
XAIRCRAFT<simulator_name>,<aircraft_id>,<icao_address>,<aircraft_type>,<registration>,<callsign>,<flight_number>
```

**Fields:**
- `simulator_name`: Name of the flight simulator (e.g., "Aerofly FS 4")
- `aircraft_id`: Unique identifier for the aircraft (16-character alphanumeric string)
- `icao_address`: ICAO 24-bit address of the aircraft
- `aircraft_type`: Type of aircraft (e.g., "C172")
- `registration`: Aircraft registration number (e.g., "N12345")
- `callsign`: Aircraft callsign
- `flight_number`: Flight number (optional)

## Custom XCOM Extension

The XCOM message is a custom extension developed for the rewinger/SkyBridge project to provide additional the state of the aircraft's communication and transponder settings.

#### XCOM Message
Used to transmit aircraft COM / XPDR settings. Send COM/Transponder packets at 1Hz (once per second):

```csv
XCOM<simulator_name>,<com1_frequency>,<com1_transmitter>,<com2_frequency>,<com2_transmitter>,<transponder_code>,<transponder_ident>,<transponder_mode>
```

**Fields:**

- `simulator_name`: Simulator Name/ID (short identifier)
- `com1_frequency` / `com2_frequency`: COM1/2 Frequency (decimal, up to 3 decimals, send 0.0 if radio cannot be listened to right now)
- `com1_transmitter` / `com2_transmitter`: COM1/2 is transmitting device (1 if this radio is set to be transmitting, 0 if not)
- `transponder_code`: Transponder code (4 octal digits interpreted as string; if it does not match this pattern assume transponder is deactivated / broken)
- `transponder_ident`: Transponder ident (1 if ident is activated on transponder, 0 if not)
- `transponder_mode`: Transponder mode ("A", "C", or "S", even though more modes may exist; send "0" to show that transponder is not sending)

## Implementation Notes

1. All messages are sent as UTF-8 encoded strings over UDP
2. Default UDP port is 49002
3. Default IP address is 127.0.0.1 (localhost)
4. Messages should be sent at appropriate intervals based on the simulation rate
5. The XAIRCRAFT message should be sent periodically to maintain aircraft metadata information

## Example Usage

```python
# Example XAIRCRAFT message (Custom Extension)
"XAIRCRAFTAerofly FS 4,ABC123DEF456GHIJ,0xABCDEF,C172,N12345,ABC123,FL123"

# Example XTRAFFIC message (ForeFlight Protocol)
"XTRAFFICAerofly FS 4,0xABCDEF,45.1234,-122.5678,5000,0,1,270,120,ABC123"

# Example XGPS message (ForeFlight Protocol)
"XGPSAerofly FS 4,-122.5678,45.1234,1524,270,61.73"

# Example XATT message (ForeFlight Protocol)
"XATTAerofly FS 4,270,0,0"

# Example XCOM message (ForeFlight Protocol)
"XCOMAerofly FS,124.025,1,119.675,7000,0,C"
```

## Future Considerations

1. Add support for additional aircraft parameters
2. Implement message validation and error checking
3. Add support for multiple aircraft tracking
4. Implement message compression for high-frequency updates
5. Add support for weather data transmission
6. Implement message acknowledgment system
8. Additional field for TCAS status

## Contributing

This protocol is part of the rewinger/SkyBridge project. The XAIRCRAFT extension is open for contributions and suggestions for improvements. Please refer to the project's contribution guidelines for more information.

## References

- ForeFlight UDP Protocol Documentation
- rewinger/SkyBridge Project Documentation 