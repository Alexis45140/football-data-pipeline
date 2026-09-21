"""Extraction des transferts depuis RapidAPI vers la table brute BigQuery."""

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timezone

import pandas as pd
import requests
from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()

API_URL = "https://free-api-live-football-data.p.rapidapi.com/football-get-all-transfers"
API_HOST = "free-api-live-football-data.p.rapidapi.com"

RAW_SCHEMA = [
    bigquery.SchemaField("joueur", "STRING"),
    bigquery.SchemaField("club_depart", "STRING"),
    bigquery.SchemaField("club_arrivee", "STRING"),
    bigquery.SchemaField("montant", "FLOAT64"),
    bigquery.SchemaField("date_transfert", "STRING"),
    bigquery.SchemaField("type_transfert", "STRING"),
    bigquery.SchemaField("_extracted_at", "TIMESTAMP"),
]

log = logging.getLogger("extract")


def fetch_page(session, page, max_retries=3):
    """Une page de l'API. Retry sur 429 et 5xx, le reste remonte."""
    for attempt in range(1, max_retries + 1):
        response = session.get(API_URL, params={"page": str(page)}, timeout=30)

        if response.status_code == 200:
            return response.json().get("response", {}).get("transfers", [])

        if response.status_code == 429 or response.status_code >= 500:
            wait = 2 ** attempt
            log.warning("page %s: HTTP %s, retry dans %ss", page, response.status_code, wait)
            time.sleep(wait)
            continue

        response.raise_for_status()

    raise RuntimeError(f"page {page}: abandon apres {max_retries} tentatives")


def parse_transfer(raw):
    fee = raw.get("fee")
    montant = fee.get("value", 0) if isinstance(fee, dict) else 0

    return {
        "joueur": raw.get("name"),
        "club_depart": raw.get("fromClub"),
        "club_arrivee": raw.get("toClub"),
        "montant": float(montant or 0),
        "date_transfert": raw.get("transferDate"),
        "type_transfert": (raw.get("transferType") or {}).get("text", "N/A"),
    }


def extract(total_pages):
    session = requests.Session()
    session.headers.update({
        "x-rapidapi-key": os.environ["RAPIDAPI_KEY"],
        "x-rapidapi-host": API_HOST,
    })

    rows = []
    for page in range(1, total_pages + 1):
        transfers = fetch_page(session, page)
        log.info("page %s: %s transferts", page, len(transfers))
        rows.extend(parse_transfer(t) for t in transfers)

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    # L'API renvoie parfois le meme transfert sur deux pages consecutives.
    before = len(df)
    df = df.drop_duplicates(subset=["joueur", "club_arrivee", "date_transfert"])
    if len(df) < before:
        log.info("%s doublons intra-batch supprimes", before - len(df))

    df["_extracted_at"] = datetime.now(timezone.utc).isoformat()
    return df


def load_to_bigquery(df, project, dataset, table):
    client = bigquery.Client(project=project)
    table_id = f"{project}.{dataset}.{table}"

    client.create_dataset(f"{project}.{dataset}", exists_ok=True)

    job_config = bigquery.LoadJobConfig(
        schema=RAW_SCHEMA,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        time_partitioning=bigquery.TimePartitioning(field="_extracted_at"),
    )
    job = client.load_table_from_json(df.to_dict("records"), table_id, job_config=job_config)
    job.result()

    log.info("%s lignes chargees dans %s", len(df), table_id)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", type=int, default=int(os.getenv("EXTRACT_PAGES", "10")))
    parser.add_argument("--dry-run", action="store_true", help="extrait sans charger dans BigQuery")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    df = extract(args.pages)
    if df.empty:
        log.error("aucune donnee recuperee")
        sys.exit(1)

    log.info("%s transferts extraits", len(df))

    if args.dry_run:
        print(df.head().to_string(index=False))
        return

    load_to_bigquery(
        df,
        project=os.environ["GCP_PROJECT"],
        dataset=os.getenv("BQ_DATASET", "football_data"),
        table=os.getenv("BQ_RAW_TABLE", "transfers_raw"),
    )


if __name__ == "__main__":
    main()
