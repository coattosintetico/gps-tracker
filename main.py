import os
import geojson
import time
import argparse
import threading
import subprocess
import atexit
from datetime import datetime

# Flag to control the execution of the script
running = True

def acquire_wakelock():
    try:
        result = subprocess.run(['termux-wake-lock'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"[{current_time_formatted()}] Wakelock acquired successfully")
            return True
        else:
            print(f"[{current_time_formatted()}] Failed to acquire wakelock: {result.stderr}")
            return False
    except Exception as e:
        print(f"[{current_time_formatted()}] Error acquiring wakelock: {str(e)}")
        return False

def release_wakelock():
    try:
        result = subprocess.run(['termux-wake-unlock'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"[{current_time_formatted()}] Wakelock released successfully")
        else:
            print(f"[{current_time_formatted()}] Failed to release wakelock: {result.stderr}")
    except Exception as e:
        print(f"[{current_time_formatted()}] Error releasing wakelock: {str(e)}")

# Register wakelock release on script exit
atexit.register(release_wakelock)

# Function to handle keyboard input
def keyboard_listener():
    global running
    while running:
        if input() == 'q':
            running = False

# Setup for keyboard listener thread
keyboard_thread = threading.Thread(target=keyboard_listener)
keyboard_thread.start()

# Function to get the current time in a specific format
def current_time_formatted():
    return datetime.now().strftime("%H:%M:%S")

# Function to create a filename with the current timestamp
def create_filename():
    # Create records directory if it doesn't exist
    records_dir = "records"
    if not os.path.exists(records_dir):
        os.makedirs(records_dir)
        print(f"[{current_time_formatted()}] Created records directory")
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return os.path.join(records_dir, f"{timestamp}.geojson")

# Function to get location with timeout
def get_location(provider, timeout=10):
    try:
        # Run termux-location with timeout
        result = subprocess.run(
            ['termux-location', '-p', provider],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        if result.returncode == 0:
            return result.stdout
        else:
            print(f"[{current_time_formatted()}] Error getting location: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        print(f"[{current_time_formatted()}] Location request timed out after {timeout} seconds")
        return None
    except Exception as e:
        print(f"[{current_time_formatted()}] Error: {str(e)}")
        return None

# Setup argument parser
parser = argparse.ArgumentParser(description='GPS Data Reader')
parser.add_argument('-t', '--time', type=int, default=60, help='Time interval in seconds')
parser.add_argument('-p', '--provider', type=str, choices=['g', 'n', 'p'], default='n',
                    help='Location provider: g=gps, n=network, p=passive')
args = parser.parse_args()

# Map provider flag to termux-location provider argument
provider_map = {
    'g': 'gps',
    'n': 'network',
    'p': 'passive'
}

# Acquire wakelock before starting
if not acquire_wakelock():
    print(f"[{current_time_formatted()}] Warning: Could not acquire wakelock. Script may not work properly when screen is locked.")

# Create a new GeoJSON file for each run
filename = create_filename()
with open(filename, 'w') as file:
    # Initialize an empty GeoJSON FeatureCollection
    feature_collection = geojson.FeatureCollection([])
    geojson.dump(feature_collection, file, indent=4)

print(f"[{current_time_formatted()}] Created new tracking file: {filename}")

# Main execution loop
while running:
    print(f"[{current_time_formatted()}] Reading gps data using {provider_map[args.provider]} provider...")

    # Get location data with timeout
    result = get_location(provider_map[args.provider])
    
    # Check if the running flag is still true
    if not running:
        break
        
    # If no result, skip this iteration
    if result is None:
        print(f"[{current_time_formatted()}] Skipping this reading due to error")
        time.sleep(args.time)
        continue

    # Parse the JSON output
    try:
        location_data = geojson.loads(result)
    except ValueError:
        print(f"[{current_time_formatted()}] Error decoding JSON from termux-location")
        print(result)
        time.sleep(args.time)
        continue

    # Create a GeoJSON feature
    feature = geojson.Feature(geometry=geojson.Point((location_data['longitude'], location_data['latitude'])),
                              properties={"timestamp": int(time.time()), 
                                        "provider": provider_map[args.provider],
                                        "additional_info": location_data})

    # Read the existing GeoJSON file, append the new feature, and write back
    with open(filename, 'r+') as file:
        data = geojson.load(file)
        data["features"].append(feature)
        file.seek(0)
        geojson.dump(data, file, indent=4)
        file.truncate()

    print(f"[{current_time_formatted()}] New record appended to {filename}")

    # Wait for the specified interval before the next iteration
    time.sleep(args.time)

# Once the loop is exited, join the keyboard thread
keyboard_thread.join()
print("Script terminated gracefully.")
