import logging
import requests
import os
from datetime import datetime
import azure.functions as func
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError

app = func.FunctionApp()

# Fetch the storage connection string from the Azure Function's Environment Variables
CONNECTION_STRING = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME = "bronze"

# =====================================================================
# SCRIPT 1: The High-Velocity Fact Stream (Station Status)
# Runs every 5 minutes: "0 */5 * * * *"
# =====================================================================
@app.timer_trigger(schedule="0 */5 * * * *", arg_name="myTimer", run_on_startup=False, use_monitor=False)
def fetch_station_status(myTimer: func.TimerRequest) -> None:
    STATUS_URL = "https://gbfs.citibikenyc.com/gbfs/en/station_status.json"
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    blob_path = f"gbfs_data/{timestamp_str}_station_status.json"

    try:
        logging.info(f"Fetching live GBFS inventory at {timestamp_str}...")
        resp = requests.get(STATUS_URL)
        resp.raise_for_status()

        blob_service_client = BlobServiceClient.from_connection_string(CONNECTION_STRING)
        blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=blob_path)

        blob_client.upload_blob(resp.text, overwrite=True)
        logging.info(f"[SUCCESS] Saved live status snapshot to ADLS Gen2: {blob_path}")

    except Exception as e:
        logging.error(f"Error fetching Station Status API: {e}")

# =====================================================================
# SCRIPT 2: The Slowly Changing Dimension (Station Information)
# Runs every Monday at midnight UTC
# =====================================================================
@app.timer_trigger(schedule="0 0 0 * * 1" , arg_name="myTimer", run_on_startup=False, use_monitor=False)
def fetch_station_information(myTimer: func.TimerRequest) -> None:
    INFO_URL = "https://gbfs.citibikenyc.com/gbfs/en/station_information.json"
    etag_blob_path = "gbfs_data/.station_info_etag"
    headers = {}

    try:
        blob_service_client = BlobServiceClient.from_connection_string(CONNECTION_STRING)
        etag_blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=etag_blob_path)

        try:
            cached_etag = etag_blob_client.download_blob().readall().decode('utf-8').strip()
            if cached_etag:
                headers['If-None-Match'] = cached_etag
        except ResourceNotFoundError:
            logging.info("No existing ETag cache found in Data Lake. Proceeding with full download.")

        logging.info(f"Checking Citi Bike Station Master List...")
        resp = requests.get(INFO_URL, headers=headers)

        if resp.status_code == 200:
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            json_blob_path = f"gbfs_data/{timestamp_str}_station_information.json"

            json_blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=json_blob_path)
            json_blob_client.upload_blob(resp.text, overwrite=True)

            new_etag = resp.headers.get("ETag")
            if new_etag:
                etag_blob_client.upload_blob(new_etag, overwrite=True)

            logging.info(f"--> [SUCCESS 200] Master list updated! Landed: {json_blob_path}")

        elif resp.status_code == 304:
            logging.info("--> [SKIPPED 304] Station geography is 100% unchanged. No file written.")
        else:
            logging.warning(f"--> [WARNING] API returned unexpected status code: {resp.status_code}")

    except Exception as e:
        logging.error(f"Failed to fetch station metadata: {e}")