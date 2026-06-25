#!/usr/bin/env python3
import os
import sys
import subprocess

# =====================================================================
# THE TROJAN HORSE: Auto-resolve 100% of dependencies at runtime
# =====================================================================
TMP_PKG_DIR = "/tmp/site_pkgs"
if not os.path.exists(TMP_PKG_DIR):
    print("Cold boot detected. Installing SDKs directly to container RAM...")
    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            f"--target={TMP_PKG_DIR}",
            "requests==2.32.3",
            "azure-storage-blob==12.20.0"
        ]
    )
sys.path.append(TMP_PKG_DIR)
# =====================================================================

import logging
import requests
from datetime import datetime
import automationassets
from azure.storage.blob import BlobServiceClient

logging.basicConfig(level=logging.INFO)

CONNECTION_STRING = automationassets.get_automation_variable("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME = "bronze"
STATUS_URL = "https://gbfs.citibikenyc.com/gbfs/en/station_status.json"

timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
blob_path = f"gbfs_data/{timestamp_str}_station_status.json"

try:
    logging.info(f"Pinging Citibike GBFS Status at {timestamp_str}...")
    resp = requests.get(STATUS_URL)
    resp.raise_for_status()

    blob_service_client = BlobServiceClient.from_connection_string(CONNECTION_STRING)
    blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=blob_path)

    blob_client.upload_blob(resp.text, overwrite=True)
    print(f"[SUCCESS] Landed live snapshot to: bronze/{blob_path}")

except Exception as e:
    print(f"[FATAL ERROR]: {e}")
    raise e