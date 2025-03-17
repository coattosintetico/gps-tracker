import subprocess
import json

def get_location():
    try:
        # Execute termux-location command and capture its output
        result = subprocess.run(['termux-location'], capture_output=True, text=True)
        
        if result.returncode == 0:
            # Parse the JSON output
            location_data = json.loads(result.stdout)
            print("Location data:", json.dumps(location_data, indent=2))
        else:
            print("Error getting location:", result.stderr)
            
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    print("Fetching location...")
    get_location()
