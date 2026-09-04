import os
import re
import html
from datetime import datetime
from typing import Optional

import psycopg
from psycopg.types.json import Jsonb
from dotenv import load_dotenv

load_dotenv()


def get_db_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def clean_html(raw_text: Optional[str]) -> str:
    if not raw_text:
        return ""

    text = html.unescape(raw_text)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)

    return text.strip()


def parse_publication_date(value: Optional[str]):
    if not value:
        return None

    try:
        cleaned_value = value.replace("Z", "+00:00")
        parsed_date = datetime.fromisoformat(cleaned_value)

        # PostgreSQL TIMESTAMP without timezone works cleanly with naive datetime
        if parsed_date.tzinfo:
            parsed_date = parsed_date.replace(tzinfo=None)

        return parsed_date

    except Exception:
        return None


def fetch_raw_jobs(conn):
    query = """
        SELECT
            id,
            source_name,
            external_job_id,
            raw_payload
        FROM jobs_raw
        ORDER BY fetched_at DESC;
    """

    with conn.cursor() as cur:
        cur.execute(query)
        return cur.fetchall()


def normalize_remotive_job(raw_job_id, source_name, external_job_id, payload):
    return {
        "raw_job_id": raw_job_id,
        "source_name": source_name,
        "external_job_id": external_job_id,
        "title": payload.get("title", "").strip(),
        "company_name": payload.get("company_name", "").strip(),
        "location": payload.get("candidate_required_location", "").strip(),
        "job_type": payload.get("job_type", "").strip(),
        "category": payload.get("category", "").strip(),
        "tags": payload.get("tags", []),
        "salary": payload.get("salary", "").strip() if payload.get("salary") else "",
        "job_url": payload.get("url", "").strip(),
        "description": clean_html(payload.get("description", "")),
        "publication_date": parse_publication_date(payload.get("publication_date")),
    }

def parse_unix_timestamp(value):
    if not value:
        return None

    try:
        return datetime.fromtimestamp(int(value))
    except Exception:
        return None


def normalize_arbeitnow_job(raw_job_id, source_name, external_job_id, payload):
    job_types = payload.get("job_types", [])
    tags = payload.get("tags", [])

    if isinstance(job_types, list):
        job_type = ", ".join(job_types)
    else:
        job_type = str(job_types or "")

    if isinstance(tags, list):
        category = ", ".join(tags[:3])
    else:
        category = str(tags or "")

    location = payload.get("location", "") or ""

    if payload.get("remote") is True:
        if location:
            location = f"Remote - {location}"
        else:
            location = "Remote"

    return {
        "raw_job_id": raw_job_id,
        "source_name": source_name,
        "external_job_id": external_job_id,
        "title": payload.get("title", "").strip(),
        "company_name": payload.get("company_name", "").strip(),
        "location": location.strip(),
        "job_type": job_type.strip(),
        "category": category.strip(),
        "tags": tags if isinstance(tags, list) else [],
        "salary": "",
        "job_url": payload.get("url", "").strip(),
        "description": clean_html(payload.get("description", "")),
        "publication_date": parse_unix_timestamp(payload.get("created_at")),
    }


def save_normalized_job(conn, job):
    query = """
        INSERT INTO jobs_normalized (
            raw_job_id,
            source_name,
            external_job_id,
            title,
            company_name,
            location,
            job_type,
            category,
            tags,
            salary,
            job_url,
            description,
            publication_date,
            normalized_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (job_url)
        DO UPDATE SET
            raw_job_id = EXCLUDED.raw_job_id,
            source_name = EXCLUDED.source_name,
            external_job_id = EXCLUDED.external_job_id,
            title = EXCLUDED.title,
            company_name = EXCLUDED.company_name,
            location = EXCLUDED.location,
            job_type = EXCLUDED.job_type,
            category = EXCLUDED.category,
            tags = EXCLUDED.tags,
            salary = EXCLUDED.salary,
            description = EXCLUDED.description,
            publication_date = EXCLUDED.publication_date,
            normalized_at = CURRENT_TIMESTAMP;
    """

    with conn.cursor() as cur:
        cur.execute(
            query,
            (
                job["raw_job_id"],
                job["source_name"],
                job["external_job_id"],
                job["title"],
                job["company_name"],
                job["location"],
                job["job_type"],
                job["category"],
                Jsonb(job["tags"]),
                job["salary"],
                job["job_url"],
                job["description"],
                job["publication_date"],
            ),
        )


def main():
    print("Starting job normalization...")

    conn = get_db_connection()

    try:
        raw_jobs = fetch_raw_jobs(conn)
        print(f"Raw jobs found: {len(raw_jobs)}")

        normalized_count = 0
        skipped_count = 0

        for raw_job_id, source_name, external_job_id, payload in raw_jobs:
            if source_name == "Remotive":
    normalized_job = normalize_remotive_job(
        raw_job_id,
        source_name,
        external_job_id,
        payload,
    )
elif source_name == "Arbeitnow":
    normalized_job = normalize_arbeitnow_job(
        raw_job_id,
        source_name,
        external_job_id,
        payload,
    )
else:
    print(f"Skipped unsupported source: {source_name}")
    skipped_count += 1
    continue

            if not normalized_job["title"] or not normalized_job["job_url"]:
                print(f"Skipped invalid job record. Raw job ID: {raw_job_id}")
                skipped_count += 1
                continue

            save_normalized_job(conn, normalized_job)
            normalized_count += 1

            print(
                f"Normalized: {normalized_job['title']} "
                f"at {normalized_job['company_name']}"
            )

        conn.commit()

        print("\nJob normalization completed.")
        print(f"Normalized jobs: {normalized_count}")
        print(f"Skipped jobs: {skipped_count}")

    except Exception as error:
        conn.rollback()
        print("Job normalization failed.")
        print(error)

    finally:
        conn.close()


if __name__ == "__main__":
    main()