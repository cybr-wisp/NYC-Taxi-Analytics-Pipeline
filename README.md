# NYC Taxi Analytics Pipeline

End-to-end data pipeline for 100M+ NYC taxi trips - Airflow, dbt, BigQuery, Docker.

## Status
In progress - Day 1 of 7 (Setup & Architecture)

## Tech Stack
- Python 3.11
- Apache Airflow 2.9
- Docker / Docker Compose
- Google Cloud Storage
- Google BigQuery
- dbt-core (dbt-bigquery)
- pandera (schema validation)
- pytest

## Repo Structure
- dags/        Airflow DAG definitions
- dbt/         dbt project (models, tests, seeds)
- scripts/     ingestion + transform Python scripts
- tests/       pytest unit/integration tests
- docs/        diagrams, screenshots, metrics
- config/      local config / GCP key (gitignored)

## Setup
1. Copy .env.example to .env and fill in GCP details
2. Place GCP service account key at config/gcp-key.json
3. docker compose up airflow-init
4. docker compose up -d
5. Open http://localhost:8080 (airflow/airflow)
