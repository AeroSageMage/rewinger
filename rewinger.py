# Copyright (c) 2024 Juan Luis Gabriel
# Modifications Copyright (c) 2025 Emanuele Bettoni
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT

"""Aircraft Tracker

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
- data can be replayed via Send_GPS_data_2.py output_GPS_data.csv
Known limitations:
- to see the replayed data, a live Aerofly FS4 session in flight must be active (or spoofed via UDP packet)

"""

import socket
import threading
import re
import tkinter as tk
from tkintermapview import TkinterMapView
from tkinter import font as tkfont
from PIL import Image, ImageTk
from typing import Optional, Dict, Any, Tuple, List
from dataclasses import dataclass
import time
import csv
# Constants
UDP_PORT = 49002
WINDOW_SIZE = "1000x600"
MAP_SIZE = (800, 600)
CONTROL_FRAME_WIDTH = 200
INFO_DISPLAY_SIZE = (24, 9)
UPDATE_INTERVAL = 1000  # milliseconds
RECEIVE_TIMEOUT = 5.0  # seconds
import csv

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
                if message.startswith('XSageMage'):
                    self.latest_aircraft_data = self._parse_aircraft_data(message)
                if message.startswith('XTRAFFIC'):
                    traffic_data = self._parse_traffic_data(message)
                    if traffic_data:
                        # Store with current timestamp
                        self.traffic_data[traffic_data.icao_address] = (traffic_data, time.time())
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
                # Extract the values
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
            return AttitudeData(*map(float, match.groups()))
        return None
    @staticmethod
    def _parse_aircraft_data(message: str) -> Optional[AircraftData]:
        """Parse Aircraft data from the received message."""
        pattern = r'^XSageMage,([A-Za-z0-9\-_]+),([A-Za-z0-9\-_]+),([A-Za-z0-9\-_]+),([A-Za-z0-9\-_]+),([A-Za-z0-9\-_]+),([A-Za-z0-9\-_]+)'
        match = re.match(pattern, message)
        if match:
            return AircraftData(*map(str, match.groups()))
        return None
    @staticmethod
    def _parse_traffic_data(message: str) -> Optional[AirTrafficData]:
        """Parse traffic data from the received message."""
        pattern = r'^XTRAFFICAerofly FS 4,([A-Za-z0-9\-_]+),([-\d.]+),([-\d.]+),([-\d.]+),([-\d.]+),([01]),'\
                r'([-\d.]+),([-\d.]+),([A-Za-z0-9\-_]+)'
        match = re.match(pattern, message)
        if match:
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
        self.log_to_csv = enabled
        status = "enabled" if enabled else "disabled"
        print(f"CSV logging {status}")

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
            
            if self.latest_attitude_data:
                with open("output_recorder/output_ATTITUDE_DATA.csv", "a") as f:
                    writer = csv.writer(f)
                    writer.writerow([self.latest_attitude_data, time.time()])
        
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

class AircraftTrackerApp:
    """
    Main application class for the Aircraft Tracker.
    Handles the GUI and updates the aircraft position on the map.
    """
    def __init__(self, master: tk.Tk):
        self.master = master
        self.master.title("Aircraft Tracker / Rewinger")
        self.master.geometry(WINDOW_SIZE)
        self.setup_ui()
        self.udp_receiver = UDPReceiver()
        self.udp_receiver.start_receiving()
        self.setup_aircraft_marker()
        # Dictionary to keep track of traffic markers
        self.traffic_markers = {}
        # Setup a different icon for traffic
        self.traffic_image = Image.open("traffic_icon.png").resize((24, 24))
        self.update_aircraft_position()

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

        # Add CSV logging toggle
        self.setup_csv_logging_toggle()

        # Add a close button
        self.close_button = tk.Button(self.control_frame, text="Close Map", command=self.close_application)
        self.close_button.pack(side="bottom", pady=10)

        # Set up the window close protocol
        self.master.protocol("WM_DELETE_WINDOW", self.close_application)

    def setup_csv_logging_toggle(self):
        """Set up the CSV logging toggle with an airplane-style illuminated button with angled stripes."""
        # Create a frame for CSV logging controls
        csv_frame = tk.Frame(self.control_frame)
        csv_frame.pack(pady=10, fill="x")
        
        # Create outer frame to contain the stripe canvas
        outer_frame = tk.Frame(csv_frame, borderwidth=0, relief=tk.RAISED)
        outer_frame.pack(side="left", padx=10)
        
        # Create a canvas for the angled warning stripes
        canvas_width, canvas_height = 130, 70
        background_color = self.master.cget("background")  # Get the parent window's background color
        stripe_canvas = tk.Canvas(outer_frame, width=canvas_width, height=canvas_height, 
                         highlightthickness=0, bg=background_color)

        stripe_canvas.pack()
        
        # Draw angled yellow/black warning stripes
        stripe_width = 10
        angle = 45  # 45-degree angle
        num_stripes = 20  # More stripes needed to cover the area with angled lines
        
        # Calculate diagonal length to ensure stripes cover the entire canvas
        diagonal_length = (canvas_width**2 + canvas_height**2)**0.5 + stripe_width*2
        offset = -diagonal_length / 2  # Start outside the canvas
        
        for i in range(0, num_stripes, 2):  # Only draw every other stripe (just the yellow ones)
            x_offset = offset + i * stripe_width
            
            # Create only the yellow stripes
            stripe_canvas.create_polygon(
                x_offset, 0,
                x_offset + stripe_width, 0,
                x_offset + stripe_width + canvas_height, canvas_height,
                x_offset + canvas_height, canvas_height,
                fill="yellow", outline=""
            )
        
        # Create a variable to track button state
        self.csv_logging_var = tk.BooleanVar(value=False)
        
        # Create a center frame for the button that will be placed over the stripes
        button_frame = tk.Frame(stripe_canvas, borderwidth=0, relief=tk.RAISED, bg="dark gray")
        button_window = stripe_canvas.create_window(canvas_width/2, canvas_height/2, window=button_frame)
        
        # Create the illuminated button
        self.csv_logging_button = tk.Button(
            button_frame,
            text="LOG DATA",
            font=("Arial", 10, "bold"),
            bg="gray25",  # Default state is off (darker gray)
            fg="white",
            activebackground="gray40",
            activeforeground="white",
            relief=tk.RAISED,
            borderwidth=0,
            width=8,
            height=1,
            command=self.toggle_csv_logging
        )
        self.csv_logging_button.pack(padx=2, pady=2)
        
        # Create a status label
        self.csv_status = tk.Label(
            csv_frame, 
            text="CSV Logging: OFF", 
            fg="red",
            font=("Arial", 10, "bold")
        )
        self.csv_status.pack(side="left", padx=10)

    def toggle_csv_logging(self):
        """Toggle CSV logging on or off and update button appearance."""
        # Toggle the state
        is_logging = not self.csv_logging_var.get()
        self.csv_logging_var.set(is_logging)
        
        # Set CSV logging
        self.udp_receiver.set_csv_logging(is_logging)
        
        # Update button appearance and status label
        if is_logging:
            # Illuminated state
            self.csv_logging_button.config(
                bg="#00ff00",  # Bright green when active
                fg="black",
                activebackground="#00cc00",
                relief=tk.SUNKEN
            )
            self.csv_status.config(text="CSV Logging: ON", fg="green")
        else:
            # Off state
            self.csv_logging_button.config(
                bg="gray25",
                fg="white",
                activebackground="gray40",
                relief=tk.RAISED
            )
            self.csv_status.config(text="CSV Logging: OFF", fg="red")
    def setup_map_selection(self):
        """Set up the map selection listbox."""
        tk.Label(self.control_frame, text="Select Map:").pack(pady=(10, 5))

        listbox_frame = tk.Frame(self.control_frame)
        listbox_frame.pack(padx=0, pady=5)

        self.map_listbox = tk.Listbox(listbox_frame, width=24, height=13)
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
        self.info_display.pack(padx=10, pady=10)

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
        if data['connected']:
            self.connection_status.config(text="Connected", fg="green")
            if data['gps'] and data['attitude'] or data['traffic']:
                self.update_map_and_marker(data)
                self.update_info_display(data)
                self.update_traffic_markers(data['traffic'])
        else:
            self.connection_status.config(text="Disconnected", fg="red")
            self.clear_info_display()
            self.clear_traffic_markers()

        self.master.after(UPDATE_INTERVAL, self.update_aircraft_position)

    def clear_info_display(self):
        """Clear the information display when disconnected."""
        self.info_display.delete(1.0, tk.END)
        self.info_display.insert(tk.END, "Waiting for data...")

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

    def clear_traffic_markers(self):
        """Remove all traffic markers from the map."""
        for marker in self.traffic_markers.values():
            marker.delete()
        self.traffic_markers = {}

    def update_map_and_marker(self, data: Dict[str, Any]):
        """Update the map view and aircraft marker with the latest data."""
        gps_data: GPSData = data['gps']
        attitude_data: AttitudeData = data['attitude']
        aircraft_data: AircraftData = data['aircraft']
        
        if not self.initial_position_set:
            self.map_widget.set_position(gps_data.latitude, gps_data.longitude)
            self.map_widget.set_zoom(10)
            self.initial_position_set = True

        self.rotated_image = self.rotate_image(attitude_data.true_heading)

        if self.aircraft_marker:
            self.aircraft_marker.delete()
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
                text="NO DATA"
            )
        
        self.map_widget.set_position(gps_data.latitude, gps_data.longitude)

    def update_info_display(self, data: Dict[str, Any]):
        """Update the information display with the latest aircraft data."""
        gps_data: GPSData = data['gps']
        attitude_data: AttitudeData = data['attitude']

        alt_ft = gps_data.altitude * 3.28084  # Convert meters to feet
        ground_speed_kts = gps_data.ground_speed * 1.94384  # Convert m/s to knots

        info_text = "=" * 24 + "\n"
        info_text += f"{'Latitude:':<15}{gps_data.latitude:>8.2f}°\n"
        info_text += f"{'Longitude:':<15}{gps_data.longitude:>8.2f}°\n"
        info_text += f"{'Altitude:':<15}{alt_ft:>6.0f} ft\n"
        info_text += f"{'Ground Speed:':<15}{ground_speed_kts:>5.2f} kts\n"
        info_text += f"{'True Heading:':<15}{attitude_data.true_heading:>8.2f}°\n"
        info_text += f"{'Pitch:':<15}{attitude_data.pitch:>8.2f}°\n"
        info_text += f"{'Roll:':<15}{attitude_data.roll:>8.2f}°\n"
        info_text += "=" * 24 + "\n"

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
        self.udp_receiver.stop()
        self.master.destroy()

if __name__ == "__main__":
    print("Starting Aircraft Tracker...")
    print(f"Listening for UDP data on port {UDP_PORT}...")
    root = tk.Tk()
    app = AircraftTrackerApp(root)
    root.mainloop()