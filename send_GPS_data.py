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

def send_traffic_data(csv_filename):
    """
    Read GPS data from specified CSV file and send it via UDP
    
    Args:
        csv_filename (str): Path to the CSV file containing GPS data
    """
    UDP_IP = "127.0.0.1"
    UDP_PORT = 49002
    airborne_flag = 1
    
    print("UDP target IP:", UDP_IP)
    print("UDP target port:", UDP_PORT)
    print(f"Reading GPS data from: {csv_filename}")
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
            
            TRAFF_MESSAGE = "XTRAFFICAerofly FS 4,"+ icao_address +"," + i[1] + "," + i[0] + "," + i[2] + "," +"0.0" + "," + str(airborne_flag) + "," + i[5] + "," + i[4] +","+callsign
            sock.sendto(bytes(TRAFF_MESSAGE, "utf-8"), (UDP_IP, UDP_PORT))
            line_count = line_count + 1
            print(line_count,TRAFF_MESSAGE,i[8])
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
        print("Usage: python Send_GPS_data_2.py <csv_filename>")
        print("Example: python Send_GPS_data_2.py output_GPS_DATA.csv")
        sys.exit(1)
    
    # Get the filename from command line argument
    csv_filename = sys.argv[1]
    
    # Process and send the data
    send_traffic_data(csv_filename)

if __name__ == "__main__":
    main()