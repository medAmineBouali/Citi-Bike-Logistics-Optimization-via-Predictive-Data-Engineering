import requests
import json
import time
import os
from datetime import datetime

# 1. Define your local mock Azure Data Lake Bronze Zone path
BRONZE_DIR = "../data/bronze/real_time/"
os.makedirs(BRONZE_DIR, exist_ok=True)

# 2. Define the high-velocity live inventory endpoint strictly
STATUS_URL = "https://gbfs.citibikenyc.com/gbfs/en/station_status.json"


def fetch_and_store_station_status():
    # Create a timestamp string to uniquely name each live snapshot file
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")

    try:
        # Fetch real-time status (live inventory only)
        status_resp = requests.get(STATUS_URL)
        status_filename = f"{BRONZE_DIR}{timestamp_str}_station_status.json"

        with open(status_filename, "w") as f:
            json.dump(status_resp.json(), f)

        print(f"[{timestamp_str}] Successfully saved live status snapshot to {BRONZE_DIR}")

    except Exception as e:
        print(f"[{datetime.now().strftime('%Y%m%d_%H%M%S')}] Error fetching Station Status API: {e}")


if __name__ == "__main__":
    print("Starting local GBFS Station Status (Fact Stream) ingestion...")
    print("This will run continuously. Press Ctrl+C in the terminal to stop.")

    # 3. Create a loop to run the extraction continuously
    while True:
        fetch_and_store_station_status()

        # Pause the script for 5 minutes (300 seconds) before the next ping
        time.sleep(300)