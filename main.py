import os
import geojson
import time
import argparse
import threading
from datetime import datetime

# Flag to control the execution of the script
running = True

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
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return f"{timestamp}.geojson"

# Setup argument parser
parser = argparse.ArgumentParser(description='GPS Data Reader')
parser.add_argument('-t', '--time', type=int, default=60, help='Time interval in seconds')
args = parser.parse_args()

# Create a new GeoJSON file for each run
filename = create_filename()
with open(filename, 'w') as file:
    # Initialize an empty GeoJSON FeatureCollection
    feature_collection = geojson.FeatureCollection([])
    geojson.dump(feature_collection, file, indent=4)

# Main execution loop
while running:
    print(f"[{current_time_formatted()}] Reading gps data...")

    # Run termux-location and capture its output
    result = os.popen('termux-location -p network').read()

    # Check if the running flag is still true
    if not running:
        break

    # Parse the JSON output
    try:
        location_data = geojson.loads(result)
    except ValueError:
        print(f"[{current_time_formatted()}] Error decoding JSON from termux-location")
        print(result)
        continue

    # Create a GeoJSON feature
    feature = geojson.Feature(geometry=geojson.Point((location_data['longitude'], location_data['latitude'])),
                              properties={"timestamp": int(time.time()), "additional_info": location_data})

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
