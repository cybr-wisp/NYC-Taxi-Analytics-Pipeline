
# Imports:
import logging
import sys 
from ingest_taxi_data import get_gcs_client, get_bucket, load_manifest, save_manifest, ingest_month

# set-up basic logging config + a logger
logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

def main():
    client = get_gcs_client()
    bucket = get_bucket(client)
    manifest = load_manifest(bucket)

    test_year = 2024
    test_month = 1

    status = ingest_month(bucket, manifest, test_year, test_month )

    save_manifest(bucket, manifest)

    logger.info(f"{status}")

    if status not in ("ingested", "skipped"):        
        logger.error("smoke test failed")
        sys.exit(1)

    logger.info("first run passed")
    logger.info("Running again to verify idempotency...")
    status_2 = ingest_month(bucket, manifest, test_year, test_month)
    logger.info(f"Second run result: {status_2}")

    if status_2 != "skipped":
        logger.error("IDEMPOTENCY CHECK FAILED — second run should have skipped")
        sys.exit(1)

    logger.info("Idempotency check PASSED")

if __name__ == "__main__":
    main()