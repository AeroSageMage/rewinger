# Copyright (c) 2025 Emanuele Bettoni
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import threading
import time
import socket
from read_my_csv import extract_gps_from_csv
import random
import string
class GPSDataSenderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("GPS Data Sender")
        self.root.geometry("700x600")
        self.root.resizable(True, True)
        
        # Variables
        self.file_path = tk.StringVar()
        self.mode = tk.StringVar(value="traffic")
        self.status = tk.StringVar(value="Ready")
        self.sending_active = False
        self.send_thread = None
        
        # Aircraft metadata variables
        self.icao_address = tk.StringVar(value="")
        self.callsign = tk.StringVar(value="")
        self.simulator_name = tk.StringVar(value="Aerofly FS 4")
        self.aircraft_type = tk.StringVar(value="C172")
        self.registration = tk.StringVar(value="N12345")
        self.flight_number = tk.StringVar(value="")
        self.aircraft_id = tk.StringVar(value=self.generate_random_id())

        # UDP settings
        self.udp_ip = tk.StringVar(value="127.0.0.1")
        self.udp_port = tk.IntVar(value=49002)
        
        # Create UI
        self.create_widgets()
        
    def create_widgets(self):
        # Main frame with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # File selection section
        file_frame = ttk.LabelFrame(main_frame, text="File Selection", padding="5")
        file_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Entry(file_frame, textvariable=self.file_path, width=60).pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill=tk.X)
        ttk.Button(file_frame, text="Browse...", command=self.browse_file).pack(side=tk.RIGHT, padx=5, pady=5)
        
        # Mode selection section
        mode_frame = ttk.LabelFrame(main_frame, text="Mode Selection", padding="5")
        mode_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Radiobutton(mode_frame, text="Traffic Mode", variable=self.mode, value="traffic").pack(side=tk.LEFT, padx=20, pady=5)
        ttk.Radiobutton(mode_frame, text="GPS Mode", variable=self.mode, value="gps").pack(side=tk.LEFT, padx=20, pady=5)
        
        # UDP Settings section
        udp_frame = ttk.LabelFrame(main_frame, text="UDP Settings", padding="5")
        udp_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(udp_frame, text="IP Address:").grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)
        ttk.Entry(udp_frame, textvariable=self.udp_ip, width=15).grid(row=0, column=1, padx=5, pady=2, sticky=tk.W)
        
        ttk.Label(udp_frame, text="Port:").grid(row=0, column=2, padx=5, pady=2, sticky=tk.W)
        ttk.Entry(udp_frame, textvariable=self.udp_port, width=6).grid(row=0, column=3, padx=5, pady=2, sticky=tk.W)
        
        # Aircraft metadata section
        metadata_frame = ttk.LabelFrame(main_frame, text="Aircraft Metadata", padding="5")
        metadata_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Column 1
        ttk.Label(metadata_frame, text="Simulator:").grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)
        ttk.Entry(metadata_frame, textvariable=self.simulator_name, width=15).grid(row=0, column=1, padx=5, pady=2, sticky=tk.W)
        
        ttk.Label(metadata_frame, text="ICAO Address:").grid(row=1, column=0, padx=5, pady=2, sticky=tk.W)
        ttk.Entry(metadata_frame, textvariable=self.icao_address, width=15).grid(row=1, column=1, padx=5, pady=2, sticky=tk.W)
        
        ttk.Label(metadata_frame, text="Callsign:").grid(row=2, column=0, padx=5, pady=2, sticky=tk.W)
        ttk.Entry(metadata_frame, textvariable=self.callsign, width=15).grid(row=2, column=1, padx=5, pady=2, sticky=tk.W)
        
        # Column 2
        ttk.Label(metadata_frame, text="Aircraft Type:").grid(row=0, column=2, padx=5, pady=2, sticky=tk.W)
        ttk.Entry(metadata_frame, textvariable=self.aircraft_type, width=15).grid(row=0, column=3, padx=5, pady=2, sticky=tk.W)
        
        ttk.Label(metadata_frame, text="Registration:").grid(row=1, column=2, padx=5, pady=2, sticky=tk.W)
        ttk.Entry(metadata_frame, textvariable=self.registration, width=15).grid(row=1, column=3, padx=5, pady=2, sticky=tk.W)
        
        ttk.Label(metadata_frame, text="Flight Number:").grid(row=2, column=2, padx=5, pady=2, sticky=tk.W)
        ttk.Entry(metadata_frame, textvariable=self.flight_number, width=15).grid(row=2, column=3, padx=5, pady=2, sticky=tk.W)
        ttk.Label(metadata_frame, text="Aircraft ID:").grid(row=3, column=0, padx=5, pady=2, sticky=tk.W)
        ttk.Entry(metadata_frame, textvariable=self.aircraft_id, width=20).grid(row=3, column=1, padx=5, pady=2, sticky=tk.W)
        ttk.Button(metadata_frame, text="Regenerate", command=lambda: self.aircraft_id.set(self.generate_random_id())).grid(row=3, column=2, padx=5, pady=2, sticky=tk.W)
        # Custom Message section
        custom_msg_frame = ttk.LabelFrame(main_frame, text="Custom UDP Message", padding="5")
        custom_msg_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.custom_message = scrolledtext.ScrolledText(custom_msg_frame, height=3)
        self.custom_message.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(custom_msg_frame, text="Send Custom Message", command=self.send_custom_message).pack(side=tk.RIGHT, padx=5, pady=5)
        
        # Action buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=10)
        
        self.start_button = ttk.Button(button_frame, text="Start Sending", command=self.start_sending)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="Stop", command=self.stop_sending, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # Log and status section
        status_frame = ttk.LabelFrame(main_frame, text="Status and Log", padding="5")
        status_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        ttk.Label(status_frame, textvariable=self.status).pack(anchor=tk.W, padx=5, pady=2)
        
        # Add log text widget
        self.log_text = scrolledtext.ScrolledText(status_frame, height=10)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
    def browse_file(self):
        filename = filedialog.askopenfilename(
            title="Select CSV file",
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*"))
        )
        if filename:
            self.file_path.set(filename)
            self.log(f"Selected file: {filename}")
    
    def log(self, message):
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)  # Auto-scroll to bottom
        
    def start_sending(self):
        if not self.file_path.get():
            self.log("Error: No file selected.")
            return
            
        if not os.path.exists(self.file_path.get()):
            self.log(f"Error: File '{self.file_path.get()}' not found.")
            return
            
        # Disable start button, enable stop button
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        
        # Start sending in a separate thread
        self.sending_active = True
        self.send_thread = threading.Thread(target=self.send_data_thread)
        self.send_thread.daemon = True
        self.send_thread.start()
        
    def stop_sending(self):
        self.sending_active = False
        self.status.set("Stopped")
        self.log("Sending stopped by user")
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        
    def send_custom_message(self):
        message = self.custom_message.get("1.0", tk.END).strip()
        if not message:
            self.log("Error: No message to send")
            return
            
        try:
            # Create UDP socket and send message
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(bytes(message, "utf-8"), (self.udp_ip.get(), self.udp_port.get()))
            self.log(f"Custom message sent: {message}")
        except Exception as e:
            self.log(f"Error sending custom message: {str(e)}")
    
    def generate_random_id(self):
        """
        Generate a random alphanumeric string of specified length.
        
        Args:
            length: Length of the random string (default: 16)
            
        Returns:
            A random alphanumeric string
        """
        # Define the character set (uppercase letters, lowercase letters, and digits)
        characters = string.ascii_letters + string.digits
        
        # Generate the random string
        random_id = ''.join(random.choice(characters) for _ in range(16))
        
        return random_id

    def send_data_thread(self):
        """Thread function for sending GPS data"""
        self.log(f"Starting to send data from {self.file_path.get()} in {self.mode.get()} mode")
        self.status.set("Sending...")
        
        try:
            # Extract data from CSV
            gps_att_time_data, file_icao, file_callsign = extract_gps_from_csv(self.file_path.get())
            
            # Use metadata from file if not specified in GUI
            icao_address = self.icao_address.get() if self.icao_address.get() else file_icao
            callsign = self.callsign.get() if self.callsign.get() else file_callsign
            
            # Create UDP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            airborne_flag = 1
            simulator_name = self.simulator_name.get()
            
            self.log(f"UDP target: {self.udp_ip.get()}:{self.udp_port.get()}")
            self.log(f"ICAO Address: {icao_address}, Callsign: {callsign}")
            
            # Send aircraft data message if in traffic mode
            if self.mode.get().lower() == "traffic":
                # Send XSageMage aircraft info message
                aircraft_info = (
                    f"XAIRCRAFT{simulator_name},{self.aircraft_id.get()},{icao_address},{self.aircraft_type.get()},"
                    f"{self.registration.get()},{callsign},{self.flight_number.get()}"
                )
                sock.sendto(bytes(aircraft_info, "utf-8"), (self.udp_ip.get(), self.udp_port.get()))
                self.log(f"Sent aircraft info: {aircraft_info}")
            
            # Main sending loop
            line_count = 0
            aircraft_info = (
                    f"XAIRCRAFT{simulator_name},{self.aircraft_id.get()},{icao_address},{self.aircraft_type.get()},"
                    f"{self.registration.get()},{callsign},{self.flight_number.get()}"
                )
            print(aircraft_info)
            for i in gps_att_time_data:
                if not self.sending_active:
                    break
                    
                # Update UI from thread
                self.root.after(0, lambda count=line_count: self.status.set(f"Sending: line {count}"))
                
                if self.mode.get().lower() == "traffic":
                    # XTRAFFIC<simulator_name>,<icao_address>,<latitude>,<longitude>,<altitude_ft>,<vertical_speed_ft/min>,<airborne_flag>,<heading_true>,<velocity_knots>,<callsign>
                    message = f"XTRAFFIC{simulator_name},{icao_address},{i[1]},{i[0]},{i[2]},0.0,{airborne_flag},{i[5]},{i[4]},{callsign}"
                    sock.sendto(bytes(message, "utf-8"), (self.udp_ip.get(), self.udp_port.get()))
                else:  # GPS mode
                    # XGPS<simulator_name>,<longitude>,<latitude>,<altitude_msl>,<track_true_north>,<groundspeed_m/s>
                    message = f"XGPS{simulator_name},{i[0]},{i[1]},{i[2]},{i[3]},{i[4]}"
                    message2 = f"XATT{simulator_name},{i[5]},{i[6]},{i[7]}"
                    #message3 = f"XTRAFFIC{simulator_name},{icao_address},{i[1]},{i[0]},{i[2]},0.0,{airborne_flag},{i[5]},{i[4]},{callsign}"
                    sock.sendto(bytes(aircraft_info, "utf-8"), (self.udp_ip.get(), self.udp_port.get()))
                    sock.sendto(bytes(message, "utf-8"), (self.udp_ip.get(), self.udp_port.get()))
                    sock.sendto(bytes(message2, "utf-8"), (self.udp_ip.get(), self.udp_port.get()))
                
                line_count += 1
                self.root.after(0, lambda msg=f"Line {line_count}: {message}": self.log(msg))
                #self.root.after(0, lambda msg=f"Line {line_count}: {message2}": self.log(msg))
                self.root.after(0, lambda msg=f"Line {line_count}: {aircraft_info}": self.log(msg))
                
                # Wait for the next data point
                time.sleep(float(i[8]))
                
            # Finalize
            if self.sending_active:  # Only if not stopped by user
                self.root.after(0, lambda: self.log(f"Finished sending all {line_count} data points"))
                self.root.after(0, lambda: self.status.set("Completed"))
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.root.after(0, lambda msg=error_msg: self.log(msg))
            self.root.after(0, lambda: self.status.set("Error"))
        finally:
            # Re-enable start button, disable stop button
            self.root.after(0, lambda: self.start_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.stop_button.config(state=tk.DISABLED))
            self.sending_active = False

def main():
    root = tk.Tk()
    app = GPSDataSenderApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()