#!/usr/bin/env python3
import os
import sys
import subprocess

# =====================================================================
# THE TROJAN HORSE: Auto-resolve dependencies on weekly cold-boots
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
from azure.core.exceptions import ResourceNotFoundError

logging.basicConfig(level=logging.INFO)

CONNECTION_STRING = automationassets.get_automation_variable("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME = "bronze"
INFO_URL = "https://gbfs.citibikenyc.com/gbfs/en/station_information.json"
etag_blob_path = "gbfs_data/.station_info_etag"
headers = {}

blob_service_client = BlobServiceClient.from_connection_string(CONNECTION_STRING)
etag_blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=etag_blob_path)

try:
    cached_etag = etag_blob_client.download_blob().readall().decode('utf-8').strip()
    if cached_etag:
        headers['If-None-Match'] = cached_etag
except ResourceNotFoundError:
    print("No existing ETag found in Data Lake. Doing full initial pull.")

print("Checking Citibike Master Station list...")
resp = requests.get(INFO_URL, headers=headers)

if resp.status_code == 200:
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_blob_path = f"gbfs_data/{timestamp_str}_station_information.json"

    json_blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=json_blob_path)
    json_blob_client.upload_blob(resp.text, overwrite=True)

    new_etag = resp.headers.get("ETag")
    if new_etag:
        etag_blob_client.upload_blob(new_etag, overwrite=True)

    print(f"--> [SUCCESS 200] Master list updated! Landed: {json_blob_path}")

elif resp.status_code == 304:
    print("--> [SKIPPED 304] Station geography is 100% unchanged. Saved 0 bytes.")
else:
    print(f"--> [WARNING] API returned unexpected code: {resp.status_code}")