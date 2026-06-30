

import argparse      # lets you run the script with command-line flags like --start-year 2022
import json          # the manifest file is stored as JSON — need this to read/write it
import logging       # for proper logging instead of print() statements
import os            # to read environment variables (GCS_BUCKET_NAME, etc.) via os.environ
import sys           # to exit with a proper error code if the run fails (sys.exit(1))
import time          # for the exponential backoff sleep between retries
from datetime import datetime, timezone   # to timestamp/measure how long the run took

import requests                              # makes the HTTP call to download from NYC TLC
from dotenv import load_dotenv               # loads your .env file into os.environ
from google.cloud import storage             # the GCS SDK — client, bucket, blob objects
from google.api_core.exceptions import NotFound  # specific exception GCS raises when a blob doesn't exist yet


load_dotenv() #loads your .env into the environment when the script starts
logger = logging.getLogger(__name__)
TLC_BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# creates the GCS connection client - this talks to the Google's servers
def get_gcs_client():
    return storage.Client()

def get_bucket(client):
    bucket_name = os.environ.get("GCS_BUCKET_NAME")
    return client.bucket(bucket_name)

MANIFEST_BLOB_PATH = "raw/_manifest.json"

def load_manifest(bucket):
    try:
        blob = bucket.blob(MANIFEST_BLOB_PATH)
        contents = blob.download_as_text()
        # now parse contents from a JSON string into a Python dict and return it
        return json.loads(contents)
    
    except NotFound:
        return {"ingested": []}
    

def save_manifest(bucket, manifest):
    json_string = json.dumps(manifest)
    bucket.blob(MANIFEST_BLOB_PATH).upload_from_string(json_string, content_type="application/json")


TAXI_TYPE = "yellow"

def blob_path_for(year, month):
    return f"raw/{year}/{month:02d}/{TAXI_TYPE}_tripdata_{year}-{month:02d}.parquet"


def already_ingested(manifest, year, month):
    key = f"{year}-{month:02d}"

    return key in manifest["ingested"]


def mark_ingested(manifest, year, month):
    key = f"{year}-{month:02d}"

    if key not in manifest["ingested"]:
        manifest["ingested"].append(key)


def download_with_retry(url, max_retries=3, timeout=90):

    for attempt in range(1, max_retries+1):
        try:
            response = requests.get(url, timeout=timeout)

            if response.status_code == 404:
                return None
            
            response.raise_for_status()
            return response.content

        except requests.exceptions.RequestException as e:
            if attempt < max_retries:
                time.sleep(2**attempt) 
            else:
                raise 


def ingest_month(bucket, manifest, year, month):
    blob_path = blob_path_for(year, month)

    if already_ingested(manifest, year, month):
        logger.info(f"{year}-{month:02d} already in manifest — skipping")
        return "skipped"
    
    blob = bucket.blob(blob_path)
    if blob.exists():
        logger.info(f"{blob_path} already exists in GCS — skipping download, updating manifest")
        mark_ingested(manifest, year, month)
        return "skipped"

    url = f"{TLC_BASE_URL}/{TAXI_TYPE}_tripdata_{year}-{month:02d}.parquet"
    logger.info(f"Downloading {url}")

    content = download_with_retry(url)
    if content is None:
        return "not_found"

    blob.upload_from_string(content, content_type="application/octet-stream")
    size_mb = len(content) / (1024 * 1024)
    logger.info(f"Uploaded {blob_path} ({size_mb:.1f} MB)")

    mark_ingested(manifest, year, month)
    return "ingested"


def run_ingestion(start_year, end_year):

    client = get_gcs_client()
    bucket = get_bucket(client)

    manifest = load_manifest(bucket)
    results = {"ingested": 0, "skipped":0, "not_found":0}

    run_start = datetime.now(timezone.utc)

    for year in range(start_year, end_year +1):
        for month in range(1,13):
            if year == run_start.year and month > run_start.month:
                continue 

            status = ingest_month(bucket, manifest, year, month)
            results[status] += 1 

    save_manifest(bucket, manifest)

    duration = (datetime.now(timezone.utc) - run_start).total_seconds()
    logger.info(
        f"Run complete in {duration:.1f}s — "
        f"ingested={results['ingested']}, skipped={results['skipped']}, not_found={results['not_found']}"
    )
    return results



def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--start-year", type=int, default=2022)
    parser.add_argument("--end-year", type=int, default=2024)

    # parse the arguments 
    args = parser.parse_args()

    try:
        results = run_ingestion(args.start_year, args.end_year)
        logger.info(f"Final results: {results}")
    except Exception as e:
        logger.error(f"Ingestion run failed: {e}")
        sys.exit(1)



    
if __name__ == "__main__":
    main()