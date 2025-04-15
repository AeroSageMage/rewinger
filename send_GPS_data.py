# Copyright (c) 2025 Emanuele Bettoni
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
import time
import socket
import sys
from read_my_csv import extract_gps_from_csv

class GPSData:
    """Dataclass to store GPS data received from the flight simulator."""
    longitude: float
    latitude: float
    altitude: float
    track: float
    ground_speed: float

class AttitudeData:
    """Dataclass to store attitude data received from the flight simulator."""
    true_heading: float
    pitch: float
    roll: float
    
class AircraftData:
    """Dataclass to store airplane data received from the network."""
    id: str # Unique identifier for this particular aircraft instance
    type_id: str # ID of the plane model from a predefined list/table
    registration: str # Official registration number assigned to the airplane by its national aviation authority
    callsign: str # Assigned radio call sign used by air traffic control and pilots for identification purposes
    icao24: str # International Civil Aviation Organization's unique four-character identifier for this aircraft
    FlightNumber: str

def send_data(csv_filename, mode="traffic"):
    """
    Read GPS data from specified CSV file and send it via UDP
    
    Args:
        csv_filename (str): Path to the CSV file containing GPS data
        mode (str): Mode of operation - 'traffic' or 'gps'
    """
    UDP_IP = "127.0.0.1"
    UDP_PORT = 49002
    airborne_flag = 1
    simulator_name = "Aerofly FS 4"
    icao_address = "NO_DATA"
    callsign = "NO_DATA"
    print("UDP target IP:", UDP_IP)
    print("UDP target port:", UDP_PORT)
    print(f"Reading GPS data from: {csv_filename}")
    print(f"Mode: {mode}")

    line_count = 0
    try:
        gps_att_time_data, icao_address, callsign = extract_gps_from_csv(csv_filename)
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
        
        for i in gps_att_time_data:
            #gps_att_time_data:
            # 0- longitude,
            # 1- latitude
            # 2- altitude,
            # 3- track,
            # 4- ground_speed,
            # 5- true_heading,
            # 6- pitch,
            # 7- roll,
            # 8- time_delta])
            
            if mode.lower() == "traffic":
                #print(icao_address)
                # XTRAFFIC<simulator_name>,<icao_address>,<latitude>,<longitude>,<altitude_ft>,<vertical_speed_ft/min>,<airborne_flag>,<heading_true>,<velocity_knots>,<callsign>
                message = f"XTRAFFIC{simulator_name},{icao_address},{i[1]},{i[0]},{i[2]},0.0,{airborne_flag},{i[5]},{i[4]},{callsign}"
                sock.sendto(bytes(message, "utf-8"), (UDP_IP, UDP_PORT))
            else:  # GPS mode
                # XGPS<simulator_name>,<longitude>,<latitude>,<altitude_msl>,<track_true_north>,<groundspeed_m/s>
                message = f"XGPS{simulator_name},{i[0]},{i[1]},{i[2]},{i[3]},{i[4]}"
                message2 = f"XATT{simulator_name},{i[5]},{i[6]},{i[7]}"
                sock.sendto(bytes(message, "utf-8"), (UDP_IP, UDP_PORT))
                sock.sendto(bytes(message2, "utf-8"), (UDP_IP, UDP_PORT))
            #sock.sendto(bytes(message, "utf-8"), (UDP_IP, UDP_PORT))
            line_count = line_count + 1
            print(line_count, message, i[8])
            time.sleep(float(i[8]))
        
        print(f"Finished sending all data points from {csv_filename}")
            
    except FileNotFoundError:
        print(f"Error: File '{csv_filename}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        sys.exit(1)

def main():
    # Check if filename was provided as command line argument
    if len(sys.argv) < 2:
        print("Usage: python send_GPS_data.py <csv_filename> [mode]")
        print("       mode: 'traffic' (default) or 'gps'")
        print("Example: python send_GPS_data.py output_GPS_DATA.csv gps")
        sys.exit(1)
    
    # Get the filename from command line argument
    csv_filename = sys.argv[1]
    
    # Get the mode if provided, default to 'traffic' if not
    mode = "traffic"
    if len(sys.argv) > 2:
        mode = sys.argv[2]
        if mode.lower() not in ["traffic", "gps"]:
            print("Invalid mode. Use 'traffic' or 'gps'.")
            sys.exit(1)
    
    # Process and send the data
    send_data(csv_filename, mode)

if __name__ == "__main__":
    main()