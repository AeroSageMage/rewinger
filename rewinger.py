import socket
import threading
import re
import tkinter as tk
from tkintermapview import TkinterMapView
from tkinter import font as tkfont
from tkinter import filedialog
from PIL import Image, ImageTk
from typing import Optional, Dict, Any, Tuple, List
from dataclasses import dataclass
import time
import csv
import xml.etree.ElementTree as ET
import os

# Constants
UDP_PORT = 49002
WINDOW_SIZE = "1000x800"
MAP_SIZE = (800, 600)
CONTROL_FRAME_WIDTH = 200
INFO_DISPLAY_SIZE = (24, 9)
UPDATE_INTERVAL = 1000  # milliseconds
RECEIVE_TIMEOUT = 5.0  # seconds


@dataclass
class GPSData:
    """Dataclass to store GPS data received from the flight simulator."""
    longitude: float
    latitude: float
    altitude: float
    track: float
    ground_speed: float

@dataclass
class AttitudeData:
    """Dataclass to store attitude data received from the flight simulator."""
    true_heading: float
    pitch: float
    roll: float
@dataclass    
class AircraftData:
    """Dataclass to store airplane data received from the network."""

    id: str # Unique identifier for this particular aircraft instance
    type_id: str # ID of the plane model from a predefined list/table
    registration: str # Official registration number assigned to the airplane by its national aviation authority
    callsign: str # Assigned radio call sign used by air traffic control and pilots for identification purposes
    icao24: str # International Civil Aviation Organization's unique four-character identifier for this aircraft
    FlightNumber: str

@dataclass
class AirTrafficData:
    """Dataclass to store traffic data received from the network."""
    icao_address: str
    latitude: float
    longitude: float
    altitude_ft: float
    vertical_speed_ft_min: float
    airborne_flag: int
    heading_true: float
    velocity_knots: float
    callsign: str
    


class UDPReceiver:
    """
    Class responsible for receiving and parsing UDP data from the flight simulator.
    """
    def __init__(self, port: int = UDP_PORT):
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.latest_gps_data: Optional[GPSData] = None
        self.latest_attitude_data: Optional[AttitudeData] = None
        self.latest_aircraft_data: Optional[AircraftData] = None
        self.traffic_data: Dict[str, Tuple[AirTrafficData, float]] = {}  # Store traffic data with timestamp
        self.running: bool = False
        self.receive_thread: Optional[threading.Thread] = None
        self.last_receive_time: float = 0
        self.log_to_csv: bool = False
        self.armed_for_recording: bool = False
        self.csv_files = {}


    def start_receiving(self) -> None:
        """Initialize and start the UDP receiving thread."""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.socket.settimeout(0.5)  # Set a timeout for the socket
        self.socket.bind(('', self.port))
        self.running = True
        self.receive_thread = threading.Thread(target=self._receive_data)
        self.receive_thread.start()

    def _receive_data(self) -> None:
        """Continuously receive and parse UDP data while the thread is running."""
        while self.running:
            try:
                data, _ = self.socket.recvfrom(1024)
                self.last_receive_time = time.time()
                message = data.decode('utf-8')
                if message.startswith('XGPS'):
                    self.latest_gps_data = self._parse_gps_data(message)
                if message.startswith('XATT'):
                    self.latest_attitude_data = self._parse_attitude_data(message)
                if message.startswith('XAIRCRAFT'):
                    self.latest_aircraft_data = self._parse_aircraft_data(message)
                if message.startswith('XTRAFFIC'):
                    traffic_data = self._parse_traffic_data(message)
                    if traffic_data:
                        # Store with current timestamp
                        self.traffic_data[traffic_data.icao_address] = (traffic_data, time.time())
                        
                # Check if we need to start logging after arming
                if self.armed_for_recording and (self.latest_gps_data or len(self.traffic_data) > 0):
                    self.armed_for_recording = False
                    self.log_to_csv = True
                    print("Recording automatically started after arming")
                    # Initialize CSV files
                    timestamp = time.strftime("%Y%m%d-%H%M%S")
                    self.csv_files = {
                        'gps': open(f"output_GPS_DATA_{timestamp}.csv", "w", newline=''),
                        'attitude': open(f"output_ATTITUDE_DATA_{timestamp}.csv", "w", newline=''),
                        'traffic': open(f"output_TRAFFIC_DATA_{timestamp}.csv", "w", newline='')
                    }
                    # Write headers
                    csv.writer(self.csv_files['gps']).writerow(['Timestamp', 'Latitude', 'Longitude', 'Altitude', 'Track', 'Ground_Speed'])
                    csv.writer(self.csv_files['attitude']).writerow(['Timestamp', 'True_Heading', 'Pitch', 'Roll'])
                    csv.writer(self.csv_files['traffic']).writerow(['Timestamp', 'ICAO', 'Latitude', 'Longitude', 'Altitude_ft', 'VS_ft_min', 'Airborne', 'Heading', 'Velocity_kts', 'Callsign'])
            except socket.timeout:
                # This is expected, just continue the loop
                pass
            except Exception as e:
                print(f"Error receiving data: {e}")
    @staticmethod
    def _parse_gps_data(message: str) -> Optional[GPSData]:
        """Parse GPS data from the received message."""
        pattern = r'XGPSAerofly FS 4,([-\d.]+),([-\d.]+),([-\d.]+),([-\d.]+),([-\d.]+)'
        match = re.match(pattern, message)
        #print(match)
        if match:
            #print("Received GPS DATA")
            latitude, longitude, altitude, track, ground_speed = map(float, match.groups())
            
            # Check for the specific "menu state" condition
            if (latitude == 0.0 and longitude == 0.0 and 
                altitude == 0.0 and track == 90.0 and ground_speed == 0.0):
                # This is the menu state - return None instead
                return None
                
            # Otherwise return the valid GPS data
            return GPSData(*map(float, match.groups()))
        
        return None
    @staticmethod
    def _parse_attitude_data(message: str) -> Optional[AttitudeData]:
        """Parse attitude data from the received message."""
        pattern = r'XATTAerofly FS 4,([-\d.]+),([-\d.]+),([-\d.]+)'
        match = re.match(pattern, message)
        if match:
            #print("Received ATTITUDE DATA")
            return AttitudeData(*map(float, match.groups()))
        return None
    @staticmethod
    def _parse_aircraft_data(message: str) -> Optional[AircraftData]:
        """Parse Aircraft data from the received message."""
        #print(message)
        pattern = r'^XAIRCRAFTAerofly FS 4,([A-Za-z0-9\-_]+),([A-Za-z0-9\-_]+),([A-Za-z0-9\-_]+),([A-Za-z0-9\-_]+),([A-Za-z0-9\-_]+),([A-Za-z0-9\-_]+)'
        match = re.match(pattern, message)
        if match:
            #print("Received Aircraft Data")
            return AircraftData(*map(str, match.groups()))
        return None
    @staticmethod
    def _parse_traffic_data(message: str) -> Optional[AirTrafficData]:
        """Parse traffic data from the received message."""
        pattern = r'^XTRAFFICAerofly FS 4,([A-Za-z0-9\-_]+),([-\d.]+),([-\d.]+),([-\d.]+),([-\d.]+),([01]),'\
                r'([-\d.]+),([-\d.]+),([A-Za-z0-9\-_]+)'
        match = re.match(pattern, message)
        #print(message)
        if match:
            #print("Received TRAFFFIC DATA")
            groups = match.groups()
            #print(groups)
            # Convert strings to appropriate data types
            return AirTrafficData(
                icao_address=str(groups[0]),
                latitude=float(groups[1]),
                longitude=float(groups[2]),
                altitude_ft=float(groups[3]),
                vertical_speed_ft_min=float(groups[4]),
                airborne_flag=int(groups[5]),
                heading_true=float(groups[6]),
                velocity_knots=float(groups[7]),
                callsign=str(groups[8])
            )
        return None

    def set_csv_logging(self, enabled: bool) -> None:
        """Enable or disable CSV logging."""
        # If we're turning off logging, close any open files
        if self.log_to_csv and not enabled:
            for file in self.csv_files.values():
                file.close()
            self.csv_files = {}
            
        self.log_to_csv = enabled
        self.armed_for_recording = False
        
        # If we're turning on logging, initialize new CSV files
        if enabled:
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            self.csv_files = {
                'gps': open(f"output_GPS_DATA_{timestamp}.csv", "w", newline=''),
                'attitude': open(f"output_ATTITUDE_DATA_{timestamp}.csv", "w", newline=''),
                'traffic': open(f"output_TRAFFIC_DATA_{timestamp}.csv", "w", newline='')
            }
            # Write headers
            csv.writer(self.csv_files['gps']).writerow(['Timestamp', 'Latitude', 'Longitude', 'Altitude', 'Track', 'Ground_Speed'])
            csv.writer(self.csv_files['attitude']).writerow(['Timestamp', 'True_Heading', 'Pitch', 'Roll'])
            csv.writer(self.csv_files['traffic']).writerow(['Timestamp', 'ICAO', 'Latitude', 'Longitude', 'Altitude_ft', 'VS_ft_min', 'Airborne', 'Heading', 'Velocity_kts', 'Callsign'])
        
        status = "enabled" if enabled else "disabled"
        print(f"CSV logging {status}")
        
    def arm_recording(self) -> None:
        """Arm the recording system to start when data is received."""
        self.armed_for_recording = True
        self.log_to_csv = False
        print("Recording armed and waiting for data")

    def get_latest_data(self) -> Dict[str, Any]:
        """Return the latest received GPS and attitude data."""
        # Clean outdated traffic data (older than 30 seconds)
        current_time = time.time()
        traffic_timeout = 30.0  # seconds
        self.traffic_data = {
            icao: (data, timestamp) 
            for icao, (data, timestamp) in self.traffic_data.items() 
            if current_time - timestamp < traffic_timeout
        }
        
        # Only write to CSV if logging is enabled
        if self.log_to_csv:
            if self.latest_gps_data:
                with open("output_recorder/output_GPS_DATA.csv", "a") as f:
                    writer = csv.writer(f)
                    writer.writerow([self.latest_gps_data, self.latest_attitude_data, time.time()])
            
            #if self.latest_attitude_data:
            #    with open("output_recorder/output_ATTITUDE_DATA.csv", "a") as f:
            #        writer = csv.writer(f)
            #        writer.writerow([self.latest_attitude_data, time.time()])
        
        return {
            'gps': self.latest_gps_data,
            'attitude': self.latest_attitude_data,
            'aircraft': self.latest_aircraft_data,
            'traffic': {icao: data for icao, (data, _) in self.traffic_data.items()},
            'connected': (time.time() - self.last_receive_time) < RECEIVE_TIMEOUT
        }

    def stop(self) -> None:
        """Stop the UDP receiving thread and close the socket."""
        self.running = False
        if self.receive_thread:
            self.receive_thread.join()
        if self.socket:
            self.socket.close()
        
        # Close any open CSV files
        if self.csv_files:
            for file in self.csv_files.values():
                file.close()

class AircraftTrackerApp:
    """
    Main application class for the Aircraft Tracker.
    Handles the GUI and updates the aircraft position on the map.
    """
    def __init__(self, master: tk.Tk):
        self.master = master
        self.master.title("Aircraft Tracker / Rewinger")
        self.master.geometry(WINDOW_SIZE)
        
        # Initialize flight plan related attributes
        self.flight_plan_waypoints = []
        self.flight_plan_path = None
        self.current_kml_file = None
        
        self.setup_ui()
        self.udp_receiver = UDPReceiver()
        self.udp_receiver.start_receiving()
        self.setup_aircraft_marker()
        # Dictionary to keep track of traffic markers
        self.traffic_markers = {}
        # Setup a different icon for traffic
        self.traffic_image = Image.open("traffic_icon.png").resize((24, 24))
        self.update_aircraft_position()
        # Variables to track map center mode
        self.follow_aircraft = True
        self.map_center = None

    def setup_ui(self):
        """Set up the main user interface components."""
        self.main_frame = tk.Frame(self.master)
        self.main_frame.pack(fill="both", expand=True)

        # Create and configure the map widget
        self.map_widget = TkinterMapView(self.main_frame, width=MAP_SIZE[0], height=MAP_SIZE[1], corner_radius=0)
        self.map_widget.pack(side="left", fill="both", expand=True)

        # Create the control frame for additional UI elements
        self.control_frame = tk.Frame(self.main_frame, width=CONTROL_FRAME_WIDTH)
        self.control_frame.pack(side="right", fill="y")

        self.setup_map_selection()
        self.setup_info_display()

        # Add a connection status label
        self.connection_status = tk.Label(self.control_frame, text="Disconnected", fg="red")
        self.connection_status.pack(pady=5)

        # Add recording controls
        self.setup_recording_controls()
        
        # Add flight plan controls
        self.setup_flightplan_controls()

        # Add map control toggle
        self.setup_map_control()

        # Add a close button
        self.close_button = tk.Button(self.control_frame, text="Close Map", command=self.close_application)
        self.close_button.pack(side="bottom", pady=10)

        # Set up the window close protocol
        self.master.protocol("WM_DELETE_WINDOW", self.close_application)

    def setup_map_control(self):
        """Set up controls for map centering behavior."""
        map_control_frame = tk.Frame(self.control_frame)
        map_control_frame.pack(pady=5, fill="x")
        
        self.follow_var = tk.BooleanVar(value=True)
        self.follow_checkbox = tk.Checkbutton(
            map_control_frame, 
            text="Follow Aircraft", 
            variable=self.follow_var,
            command=self.toggle_follow_mode
        )
        self.follow_checkbox.pack(side="left", padx=5)
        
    def toggle_follow_mode(self):
        """Toggle whether the map should automatically follow the aircraft."""
        self.follow_aircraft = self.follow_var.get()
        if not self.follow_aircraft:
            # Store current map center when disabling follow mode
            current_pos = self.map_widget.get_position()
            self.map_center = (current_pos[0], current_pos[1])
            print(f"Follow mode disabled. Map center fixed at: {self.map_center}")
        else:
        # When re-enabling follow mode, if we have GPS data, immediately center on aircraft
            if self.udp_receiver.latest_gps_data:
                gps = self.udp_receiver.latest_gps_data
                self.map_widget.set_position(gps.latitude, gps.longitude)
                print("Follow mode enabled. Centering on aircraft.")    

    def setup_flightplan_controls(self):
        """Set up flight plan loading and display controls."""
        fp_frame = tk.Frame(self.control_frame, relief=tk.GROOVE, bd=2)
        fp_frame.pack(pady=5, padx=10, fill="x")
        
        # Title label
        tk.Label(fp_frame, text="Flight Plan", font=("Arial", 10, "bold")).pack(pady=(5,2))
        
        # Load button
        self.load_kml_button = tk.Button(
            fp_frame,
            text="Load KML File",
            font=("Arial", 9),
            command=self.load_kml_file,
            width=15
        )
        self.load_kml_button.pack(pady=3, padx=10)
        
        # Toggle display checkbox
        self.show_flightplan_var = tk.BooleanVar(value=False)
        self.show_flightplan_checkbox = tk.Checkbutton(
            fp_frame, 
            text="Show Flight Plan", 
            variable=self.show_flightplan_var,
            command=self.toggle_flight_plan_display
        )
        self.show_flightplan_checkbox.pack(pady=3)
        
        # Status label
        self.flightplan_status = tk.Label(
            fp_frame, 
            text="No flight plan loaded",
            font=("Arial", 9)
        )
        self.flightplan_status.pack(pady=3)

    def load_kml_file(self):
        """Open a file dialog to select and load a KML file."""
        file_path = filedialog.askopenfilename(
            title="Select SimBrief KML File",
            filetypes=[("KML files", "*.kml"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                # Store the file path
                self.current_kml_file = file_path
                
                # Parse the KML file
                self.flight_plan_waypoints = self.parse_kml_file(file_path)
                
                if self.flight_plan_waypoints:
                    # Update status
                    self.flightplan_status.config(
                        text=f"Loaded: {os.path.basename(file_path)}",
                        fg="green"
                    )
                    
                    # Set the checkbox to checked and draw the flight plan
                    self.show_flightplan_var.set(True)
                    self.draw_flight_plan(self.flight_plan_waypoints)
                else:
                    self.flightplan_status.config(
                        text="Error: No route found in KML",
                        fg="red"
                    )
            except Exception as e:
                self.flightplan_status.config(
                    text=f"Error loading KML",
                    fg="red"
                )
                print(f"Error loading KML file: {e}")

    def parse_kml_file(self, kml_file_path):
        """
        Parse a KML file and extract flight plan coordinates.
        
        Args:
            kml_file_path: Path to the KML file
            
        Returns:
            List of (latitude, longitude) tuples representing the flight plan route
        """
        try:
            # Parse the KML file
            tree = ET.parse(kml_file_path)
            root = tree.getroot()
            
            # Define the namespace
            namespace = {'kml': 'http://www.opengis.net/kml/2.2'}
            
            # Find all LineString elements which contain the flight path
            coordinates_elements = root.findall('.//kml:LineString/kml:coordinates', namespace)
            
            waypoints = []
            for coord_element in coordinates_elements:
                # KML coordinates are in lon,lat,alt format
                coord_text = coord_element.text.strip()
                for point in coord_text.split():
                    parts = point.split(',')
                    if len(parts) >= 2:
                        lon, lat = float(parts[0]), float(parts[1])
                        waypoints.append((lat, lon))  # Note: tkintermapview uses (lat, lon) order
            
            return waypoints
        except Exception as e:
            print(f"Error parsing KML file: {e}")
            return []

    def draw_flight_plan(self, waypoints):
        """
        Draw the flight plan on the map.
        
        Args:
            waypoints: List of (latitude, longitude) tuples
        """
        if not waypoints:
            return
            
        # Create a path with the waypoints
        self.flight_plan_path = self.map_widget.set_path(waypoints, 
                                                        width=3,
                                                        color="#3080FF")
                                                        
        # Fit the map to show the entire flight plan
        if self.follow_aircraft:
            # If following aircraft, don't zoom out to fit flight plan
            pass
        else:
            # Otherwise, fit the map to show the entire flight plan
            self.map_widget.fit_bounds(waypoints)

    def toggle_flight_plan_display(self):
        """Toggle the display of the flight plan on the map."""
        show_plan = self.show_flightplan_var.get()
        
        if hasattr(self, 'flight_plan_path') and self.flight_plan_path:
            # Remove existing path
            self.flight_plan_path.delete()
            self.flight_plan_path = None
            
        if show_plan and hasattr(self, 'flight_plan_waypoints') and self.flight_plan_waypoints:
            # Redraw the path
            self.draw_flight_plan(self.flight_plan_waypoints)

    def setup_recording_controls(self):
        """Set up modern recording controls."""
        # Create a frame for recording controls
        recording_frame = tk.Frame(self.control_frame)
        recording_frame.pack(pady=10, fill="x")
        
        # Create variables to track button states
        self.record_var = tk.BooleanVar(value=False)
        self.armed_var = tk.BooleanVar(value=False)
        
        # Create a styled frame for buttons
        button_frame = tk.Frame(recording_frame, relief=tk.GROOVE, bd=2)
        button_frame.pack(pady=5, padx=10, fill="x")
        
        # Title label
        tk.Label(button_frame, text="Recording Controls", font=("Arial", 10, "bold")).pack(pady=(5,2))
        
        # Create the arming button
        self.arm_button = tk.Button(
            button_frame,
            text="ARM RECORDING",
            font=("Arial", 9),
            bg="#ff9900",  # Orange for armed state
            fg="black",
            activebackground="#ffcc00",
            relief=tk.RAISED,
            command=self.toggle_arm_recording,
            width=15
        )
        self.arm_button.pack(pady=3, padx=10)
        
        # Create the record button
        self.record_button = tk.Button(
            button_frame,
            text="START RECORDING",
            font=("Arial", 9),
            bg="#cccccc",  # Gray when not active
            fg="black",
            activebackground="#dddddd",
            relief=tk.RAISED,
            command=self.toggle_csv_logging,
            width=15
        )
        self.record_button.pack(pady=3, padx=10)
        
        # Create a status label
        self.recording_status = tk.Label(
            button_frame, 
            text="Status: Ready",
            font=("Arial", 9)
        )
        self.recording_status.pack(pady=5)

    def toggle_arm_recording(self):
        """Toggle the armed state for recording."""
        is_armed = not self.armed_var.get()
        self.armed_var.set(is_armed)
        
        # Update UI
        if is_armed:
            self.arm_button.config(
                bg="#ff9900",  # Orange
                text="ARMED",
                relief=tk.SUNKEN
            )
            self.record_button.config(
                bg="#cccccc",  # Gray
                text="START RECORDING",
                relief=tk.RAISED,
                state=tk.DISABLED
            )
            self.recording_status.config(text="Status: Armed for Recording", fg="orange")
            self.record_var.set(False)
            
            # Tell the UDP receiver to arm for recording
            self.udp_receiver.arm_recording()
        else:
            self.arm_button.config(
                bg="#dddddd",  # Light gray
                text="ARM RECORDING",
                relief=tk.RAISED
            )
            self.record_button.config(
                state=tk.NORMAL
            )
            self.recording_status.config(text="Status: Ready", fg="black")
            
            # Disarm recording
            self.udp_receiver.armed_for_recording = False

    def toggle_csv_logging(self):
        """Toggle CSV logging on or off and update button appearance."""
        # Don't allow toggling if armed
        if self.armed_var.get():
            return
            
        # Toggle the state
        is_logging = not self.record_var.get()
        self.record_var.set(is_logging)
        
        # Update buttons
        if is_logging:
            # Recording state
            self.record_button.config(
                bg="#ff3333",  # Red when recording
                text="STOP RECORDING",
                relief=tk.SUNKEN
            )
            self.arm_button.config(state=tk.DISABLED)
            self.recording_status.config(text="Status: Recording", fg="#ff3333")
        else:
            # Off state
            self.record_button.config(
                bg="#dddddd",  # Light gray
                text="START RECORDING",
                relief=tk.RAISED
            )
            self.arm_button.config(state=tk.NORMAL)
            self.recording_status.config(text="Status: Ready", fg="black")
        
        # Set CSV logging
        self.udp_receiver.set_csv_logging(is_logging)

    def setup_map_selection(self):
        """Set up the map selection listbox."""
        tk.Label(self.control_frame, text="Select Map:").pack(pady=(10, 5))

        listbox_frame = tk.Frame(self.control_frame)
        listbox_frame.pack(padx=0, pady=5)

        self.map_listbox = tk.Listbox(listbox_frame, width=24, height=6)
        self.map_listbox.pack(side="left")

        for option, _ in self.get_map_options():
            self.map_listbox.insert(tk.END, option)

        self.map_listbox.bind('<<ListboxSelect>>', lambda e: self.change_map())

    def setup_info_display(self):
        """Set up the information display area."""
        tk.Label(self.control_frame, text="Aircraft Position:").pack(pady=(10, 5))

        info_font = tkfont.Font(family="Consolas", size=9)
        self.info_display = tk.Text(self.control_frame, width=INFO_DISPLAY_SIZE[0], height=INFO_DISPLAY_SIZE[1],
                                    wrap=tk.NONE, font=info_font)
        self.info_display.pack(padx=10, pady=5)

    def setup_aircraft_marker(self):
        """Set up the aircraft marker image and related variables."""
        self.aircraft_image = Image.open("aircraft_icon.png").resize((32, 32))
        self.rotated_image = ImageTk.PhotoImage(self.aircraft_image)
        self.aircraft_marker = None
        self.initial_position_set = False

    def update_aircraft_position(self):
        """
        Update the aircraft's position on the map and the information display.
        This method is called periodically to refresh the display.
        """
        data = self.udp_receiver.get_latest_data()
        
        # Check if we're connected to the simulator
        if data['connected']:
            self.connection_status.config(text="Connected", fg="green")
            
            # Update traffic markers regardless of GPS data
            if data['traffic']:
                self.update_traffic_markers(data['traffic'])
                
                # If we haven't set an initial position and we have traffic,
                # use the first traffic position to center the map
                if not self.initial_position_set and self.follow_aircraft:
                    first_traffic = next(iter(data['traffic'].values()))
                    self.map_widget.set_position(first_traffic.latitude, first_traffic.longitude)
                    self.map_widget.set_zoom(10)
                    self.initial_position_set = True
                    self.map_center = (first_traffic.latitude, first_traffic.longitude)
            # If we have GPS data, update the aircraft marker and info display
            if data['gps'] and data['attitude']:
                self.update_aircraft_marker(data)
                self.update_info_display(data)
        else:
            self.connection_status.config(text="Disconnected", fg="red")
            self.clear_info_display()
            
            # Keep traffic markers even when disconnected (just don't add new ones)
            # But clean up aircraft marker
            if self.aircraft_marker:
                self.aircraft_marker.delete()
                self.aircraft_marker = None

        # Check if armed recording should automatically start
        if self.armed_var.get() and not self.udp_receiver.armed_for_recording:
            # The UDPReceiver has detected data and auto-started recording
            if self.udp_receiver.log_to_csv:
                self.armed_var.set(False)
                self.record_var.set(True)
                self.arm_button.config(
                    bg="#dddddd",  # Light gray
                    text="ARM RECORDING",
                    relief=tk.RAISED,
                    state=tk.DISABLED
                )
                self.record_button.config(
                    bg="#ff3333",  # Red when recording
                    text="STOP RECORDING",
                    relief=tk.SUNKEN
                )
                self.recording_status.config(text="Status: Recording", fg="#ff3333")
            
        self.master.after(UPDATE_INTERVAL, self.update_aircraft_position)

    def clear_info_display(self):
        """Clear the information display when disconnected."""
        self.info_display.delete(1.0, tk.END)
        self.info_display.insert(tk.END, "Waiting for aircraft data...\n")
        
        # Display traffic count if available
        traffic_count = len(self.udp_receiver.traffic_data)
        if traffic_count > 0:
            self.info_display.insert(tk.END, f"Traffic detected: {traffic_count} aircraft")

    def update_traffic_markers(self, traffic_data):
        """Update the traffic markers on the map."""
        # Remove markers for traffic that's no longer present
        for icao in list(self.traffic_markers.keys()):
            if icao not in traffic_data:
                self.traffic_markers[icao].delete()
                del self.traffic_markers[icao]
        
        # Update existing markers and add new ones
        for icao, data in traffic_data.items():
            rotated_image = self.rotate_traffic_image(data.heading_true)
            
            if icao in self.traffic_markers:
                # Update existing marker
                self.traffic_markers[icao].delete()
            
            # Create new marker
            altitude_text = f"{int(data.altitude_ft)}'"
            marker_text = f"{data.callsign} {altitude_text}"
            
            self.traffic_markers[icao] = self.map_widget.set_marker(
                data.latitude, data.longitude,
                icon=rotated_image,
                icon_anchor="center",
                text=marker_text
            )

    def rotate_traffic_image(self, angle: float) -> ImageTk.PhotoImage:
        """Rotate the traffic icon image by the given angle."""
        return ImageTk.PhotoImage(self.traffic_image.rotate(-angle))

    def update_aircraft_marker(self, data: Dict[str, Any]):
        """Update just the aircraft marker with the latest data."""
        gps_data: GPSData = data['gps']
        attitude_data: AttitudeData = data['attitude']
        aircraft_data: AircraftData = data['aircraft']
        
        if not self.initial_position_set:
            self.map_widget.set_position(gps_data.latitude, gps_data.longitude)
            self.map_widget.set_zoom(10)
            self.initial_position_set = True
            self.map_center = (gps_data.latitude, gps_data.longitude)
        self.rotated_image = self.rotate_image(attitude_data.true_heading)

        # Update or create the aircraft marker
        if self.aircraft_marker:
            self.aircraft_marker.delete()
            
        # Create marker with appropriate text
        if aircraft_data is not None:
            self.aircraft_marker = self.map_widget.set_marker(
                gps_data.latitude, gps_data.longitude,
                icon=self.rotated_image,
                icon_anchor="center",
                text=aircraft_data.FlightNumber + " " + aircraft_data.callsign
            )
        else:
            self.aircraft_marker = self.map_widget.set_marker(
                gps_data.latitude, gps_data.longitude,
                icon=self.rotated_image,
                icon_anchor="center",
                text="Aerofly FS 4"
            )
        
        # Center map on aircraft if follow mode is enabled
        if self.follow_aircraft:
            self.map_widget.set_position(gps_data.latitude, gps_data.longitude)
        #elif self.map_center:
        #    # Stay on the fixed position when follow mode is disabled
        #    self.map_widget.set_position(self.map_center[0], self.map_center[1])

    def update_info_display(self, data: Dict[str, Any]):
        """Update the information display with the latest aircraft data."""
        gps_data: GPSData = data['gps']
        attitude_data: AttitudeData = data['attitude'] 
        aircraft_data: AircraftData = data['aircraft']

        alt_ft = gps_data.altitude * 3.28084  # Convert meters to feet
        ground_speed_kts = gps_data.ground_speed * 1.94384  # Convert m/s to knots

        info_text = "=" * 24 + "\n"
        
        # Add aircraft data if available
        if aircraft_data:
            callsign = aircraft_data.callsign if aircraft_data.callsign else "N/A"
            flight_num = aircraft_data.FlightNumber if aircraft_data.FlightNumber else "N/A"
            info_text += f"{'Callsign:':<15}{callsign}\n"
            info_text += f"{'Flight:':<15}{flight_num}\n"
        
        info_text += f"{'Latitude:':<15}{gps_data.latitude:>8.2f}°\n"
        info_text += f"{'Longitude:':<15}{gps_data.longitude:>8.2f}°\n"
        info_text += f"{'Altitude:':<15}{alt_ft:>6.0f} ft\n"
        info_text += f"{'Ground Speed:':<15}{ground_speed_kts:>5.2f} kts\n"
        info_text += f"{'True Heading:':<15}{attitude_data.true_heading:>8.2f}°\n"
        info_text += f"{'Pitch:':<15}{attitude_data.pitch:>8.2f}°\n"
        info_text += f"{'Roll:':<15}{attitude_data.roll:>8.2f}°\n"
        
        # Add traffic count
        traffic_count = len(data['traffic'])
        info_text += "=" * 24 + "\n"
        info_text += f"Traffic Count: {traffic_count}\n"

        self.info_display.delete(1.0, tk.END)
        self.info_display.insert(tk.END, info_text)

    def rotate_image(self, angle: float) -> ImageTk.PhotoImage:
        """Rotate the aircraft icon image by the given angle."""
        return ImageTk.PhotoImage(self.aircraft_image.rotate(-angle))

    def change_map(self):
        """Change the map tile server based on the user's selection."""
        selected_indices = self.map_listbox.curselection()
        if selected_indices:
            _, tile_server = self.get_map_options()[selected_indices[0]]
            self.map_widget.set_tile_server(tile_server)

    @staticmethod
    def get_map_options() -> List[Tuple[str, str]]:
        """Return a list of available map options with their tile server URLs."""
        return [
            ("OpenStreetMap", "https://a.tile.openstreetmap.org/{z}/{x}/{y}.png"),
            ("OpenStreetMap DE", "https://tile.openstreetmap.de/tiles/osmde/{z}/{x}/{y}.png"),
            ("OpenStreetMap FR", "https://a.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png"),
            ("OpenTopoMap", "https://a.tile.opentopomap.org/{z}/{x}/{y}.png"),
            ("Google Normal", "https://mt0.google.com/vt/lyrs=m&hl=en&x={x}&y={y}&z={z}"),
            ("Google Satellite", "https://mt0.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}"),
            ("Google Terrain", "https://mt0.google.com/vt/lyrs=p&hl=en&x={x}&y={y}&z={z}"),
            ("Google Hybrid", "https://mt0.google.com/vt/lyrs=y&hl=en&x={x}&y={y}&z={z}"),
            ("Carto Dark Matter", "https://cartodb-basemaps-a.global.ssl.fastly.net/dark_all/{z}/{x}/{y}.png"),
            ("Carto Positron", "https://cartodb-basemaps-a.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png"),
            ("ESRI World Imagery", "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"),
            ("ESRI World Street Map", "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}"),
            ("ESRI World Topo Map", "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}")
        ]

    def close_application(self):
        """Clean up resources and close the application."""
        print("Closing Aircraft Tracker...")
        
        # Clean up flight plan path if it exists
        if hasattr(self, 'flight_plan_path') and self.flight_plan_path:
            self.flight_plan_path.delete()
            
        self.udp_receiver.stop()
        self.master.destroy()

if __name__ == "__main__":
    print("Starting Aircraft Tracker / Rewinger")
    print(f"Listening for UDP data on port {UDP_PORT}...")
    root = tk.Tk()
    app = AircraftTrackerApp(root)
    root.mainloop()