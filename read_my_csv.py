# Copyright (c) 2025 Emanuele Bettoni
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
import csv

# Helper function to determine if a string represents a numeric value
def is_numeric(value):
    try:
        float(value)
        return True
    except ValueError:
        return False    
    
 
def extract_gps_from_csv(file_name):
    icao_address = "UNKNOWN"  # Default values in case they're not provided
    callsign = "UNKNOWN"   
    with open(file_name, "r") as f: # Open output.csv for reading in text mode (not binary)
        mylist = csv.reader(f, skipinitialspace=True) # Create a CSV reader object with leading whitespace skipped
        gps_att_time_data= []  # Initialize lists to store data from each row of the file
        t0 = True
        t1 = 0.0
        first_line = True
        for i in mylist: # Loop over all rows of output.csv
            
            if first_line:
                print(i)
                # Check if first line contains only identification data (2 strings)
                # We can verify this by checking if there are exactly 2 items
                # and if they don't look like numeric values (longitude/latitude)
                if len(i) == 2 and not is_numeric(i[0]) and not is_numeric(i[1]):
                    icao_address = i[0]
                    callsign = i[1]
                    first_line = False
                    continue  # Skip to next row as this one doesn't contain GPS data
                else:
                    # This is actually a data row, not identification
                    first_line = False
                    # Process as normal GPS data (fall through to the data extraction code)
            else:
                GPS_CSV, ATT_CSV, time_stamp = i[0],i[1],i[2] # Extract GPS longitude and latitude from first column of row using split() function on the string with commas as delimiter
                dirty_longitude, latitude, altitude, track,dirty_ground_speed = GPS_CSV.split(",")
                true_heading, pitch, roll = ATT_CSV.split(",")
                longitude = dirty_longitude.split("GPSData(")[1] 
                longitude = longitude.split("=")[1]
                latitude = latitude.split("=")[1]
                altitude = altitude.split("=")[1]
                track = track.split("=")[1]
                ground_speed = dirty_ground_speed.split(")")[0]
                ground_speed = ground_speed.split("=")[1]
                true_heading = true_heading.split("AttitudeData(")[1] 
                true_heading = true_heading.split("=")[1]
                pitch = pitch.split("=")[1]
                roll = roll.split(")")[0]
                roll = roll.split("=")[1]
                #print(time_stamp)
                #time_stamp = time_stamp.split("]")[0]
                #time_stamp = time_stamp.split("'")[1]
                #time_stamp = time_stamp.split("]")[0]
                #time_stamp = time_stamp.split("'")[1]
                if t0 == True:
                    t1 = float(time_stamp)
                    time_delta = 0
                    t0 = False
                else:
                    #print(t1,time_delta)
                    time_delta = float(time_stamp) - t1
                    t1 = float(time_stamp)
            #true_heading, pitch, roll = i[1].strip(")").split(")")[-3:] # Extract attitude data (true heading, pitch, and roll) from second column of row by stripping off parentheses with strip(), splitting on them to create a list, and then grabbing the last three items
            #timestamp.append(i[2]) # Append third item in each row to timestamp list (since it's already stored as a float value)
                time_delta = str(time_delta)
                gps_att_time_data.append([longitude, latitude, altitude, track, ground_speed,true_heading, pitch, roll,time_delta]) # Add GPS data for this iteration of the loop to its respective list
                #att_data.append([true_heading, pitch, roll]) # Add GPS data for this iteration of the loop to its respective list
                #time_delta_data.append([time_delta]) # Add GPS data for this iteration of the loop to its respective list
            #attitude_data.append([true_heading, pitch, roll]) # Add attitude data for this iteration of the loop to its respective list
        
        return(gps_att_time_data,icao_address,callsign)

def extract_attitude_from_csv(file_name):
    with open(file_name, "r") as f: # Open output.csv for reading in text mode (not binary)
        mylist = csv.reader(f, skipinitialspace=True) # Create a CSV reader object with leading whitespace skipped
        attitude_data= [] # Initialize lists to store data from each row of the file
        t0 = True
        t1 = 0.0
        for i in mylist: # Loop over all rows of output.csv
            true_heading, pitch, roll,time_stamp = str(i).split(",") # Extract GPS longitude and latitude from first column of row using split() function on the string with commas as delimiter
            true_heading = true_heading.split("AttitudeData(")[1] 
            true_heading = true_heading.split("=")[1]
            pitch = pitch.split("=")[1]
            roll = roll.split(")")[0]
            roll = roll.split("=")[1]
            time_stamp = time_stamp.split("]")[0]
            time_stamp = time_stamp.split("'")[1]
            if t0 == True:
                t1 = float(time_stamp)
                time_delta = 0
                t0 = False
            else:
                #print(t1,time_delta)
                time_delta = float(time_stamp) - t1
                t1 = float(time_stamp)
        #true_heading, pitch, roll = i[1].strip(")").split(")")[-3:] # Extract attitude data (true heading, pitch, and roll) from second column of row by stripping off parentheses with strip(), splitting on them to create a list, and then grabbing the last three items
        #timestamp.append(i[2]) # Append third item in each row to timestamp list (since it's already stored as a float value)
            time_delta = str(time_delta)
            attitude_data.append([true_heading, pitch, roll, time_delta]) # Add GPS data for this iteration of the loop to its respective list
        #attitude_data.append([true_heading, pitch, roll]) # Add attitude data for this iteration of the loop to its respective list
        
        return(attitude_data)

if __name__ == "__main__":
    gps_att_time_data = extract_gps_from_csv("output_GPS_DATA.csv")
    for i in gps_att_time_data:
        print(i)