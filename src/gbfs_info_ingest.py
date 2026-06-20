import requests
import json
import os
from datetime import datetime

# 1. Point to your mock Bronze zone
BRONZE_DIR = "../data/bronze/real_time/"
os.makedirs(BRONZE_DIR, exist_ok=True)

INFO_URL = "https://gbfs.citibikenyc.com/gbfs/en/station_information.json"

# A tiny text file used to remember the exact state of the API from the last successful download
ETAG_CACHE_FILE = os.path.join(BRONZE_DIR, ".station_info_etag")


def fetch_station_information():
    headers = {}

    # Check if we have a cached ETag hash from a previous run
    if os.path.exists(ETAG_CACHE_FILE):
        with open(ETAG_CACHE_FILE, "r") as f:
            cached_etag = f.read().strip()
            if cached_etag:
                headers['If-None-Match'] = cached_etag

    try:
        print(f"Checking Citi Bike Station Master List at {INFO_URL}...")
        resp = requests.get(INFO_URL, headers=headers)

        # HTTP 200: The server says "The station network has changed! Here is the new data."
        if resp.status_code == 200:
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{BRONZE_DIR}{timestamp_str}_station_information.json"

            with open(filename, "w") as f:
                json.dump(resp.json(), f)

            # Update our local cache file with the new ETag provided by the server
            new_etag = resp.headers.get("ETag")
            if new_etag:
                with open(ETAG_CACHE_FILE, "w") as ef:
                    ef.write(new_etag)

            print(f"--> [SUCCESS 200] Master list updated! Landed new snapshot: {filename}")

        # HTTP 304: The server says "Literally nothing has changed since your last download."
        elif resp.status_code == 304:
            print("--> [SKIPPED 304] Station geography is 100% unchanged. No file written.")

        else:
            print(f"--> [WARNING] API returned unexpected status code: {resp.status_code}")

    except Exception as e:
        print(f"Failed to fetch station metadata: {e}")


if __name__ == "__main__":
    fetch_station_information()