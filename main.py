import os
import geojson
import time
import argparse
import threading
import subprocess
import atexit
import logging
from datetime import datetime

# Flag to control the execution of the script
running = True

def setup_logging(geojson_file):
    # Create logs directory if it doesn't exist
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    # Create log filename based on geojson filename
    base_name = os.path.splitext(os.path.basename(geojson_file))[0]
    log_file = os.path.join(logs_dir, f"{base_name}.log")
    
    # Set up logging configuration
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(message)s',
        datefmt='%H:%M:%S',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    logging.info(f"Logging initialized. Log file: {log_file}")

def acquire_wakelock():
    try:
        result = subprocess.run(['termux-wake-lock'], capture_output=True, text=True)
        if result.returncode == 0:
            logging.info("Wakelock acquired successfully")
            return True
        else:
            logging.error(f"Failed to acquire wakelock: {result.stderr}")
            return False
    except Exception as e:
        logging.error(f"Error acquiring wakelock: {str(e)}")
        return False

def release_wakelock():
    try:
        result = subprocess.run(['termux-wake-unlock'], capture_output=True, text=True)
        if result.returncode == 0:
            logging.info("Wakelock released successfully")
        else:
            logging.error(f"Failed to release wakelock: {result.stderr}")
    except Exception as e:
        logging.error(f"Error releasing wakelock: {str(e)}")

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

# Function to create a filename with the current timestamp
def create_filename():
    # Create records directory if it doesn't exist
    records_dir = "records"
    if not os.path.exists(records_dir):
        os.makedirs(records_dir)
        logging.info("Created records directory")
    
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
            logging.error(f"Error getting location: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        logging.error(f"Location request timed out after {timeout} seconds")
        return None
    except Exception as e:
        logging.error(f"Error: {str(e)}")
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

# Create a new GeoJSON file for each run
filename = create_filename()

# Setup logging after we have the filename
setup_logging(filename)

# Acquire wakelock before starting
if not acquire_wakelock():
    logging.warning("Could not acquire wakelock. Script may not work properly when screen is locked.")

# Initialize the GeoJSON file
with open(filename, 'w') as file:
    # Initialize an empty GeoJSON FeatureCollection
    feature_collection = geojson.FeatureCollection([])
    geojson.dump(feature_collection, file, indent=4)

logging.info(f"Created new tracking file: {filename}")

# Main execution loop
while running:
    logging.info(f"Reading gps data using {provider_map[args.provider]} provider...")

    # Get location data with timeout
    result = get_location(provider_map[args.provider])
    
    # Check if the running flag is still true
    if not running:
        break
        
    # If no result, skip this iteration
    if result is None:
        logging.warning("Skipping this reading due to error")
        time.sleep(args.time)
        continue

    # Parse the JSON output
    try:
        location_data = geojson.loads(result)
    except ValueError:
        logging.error("Error decoding JSON from termux-location")
        logging.debug(f"Raw output: {result}")
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

    logging.info(f"New record appended to {filename}")

    # Wait for the specified interval before the next iteration
    time.sleep(args.time)

# Once the loop is exited, join the keyboard thread
keyboard_thread.join()
logging.info("Script terminated gracefully.")
