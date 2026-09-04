import os
import re
import html
from datetime import datetime
from typing import Optional, Any

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

    text = html.unescape(str(raw_text))
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</li>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)

    return text.strip()


def parse_publication_date(value: Optional[str]):
    if not value:
        return None

    try:
        cleaned_value = str(value).replace("Z", "+00:00")
        parsed_date = datetime.fromisoformat(cleaned_value)

        if parsed_date.tzinfo:
            parsed_date = parsed_date.replace(tzinfo=None)

        return parsed_date

    except Exception:
        return None


def parse_unix_timestamp(value: Any):
    if not value:
        return None

    try:
        return datetime.fromtimestamp(int(value))
    except Exception:
        return None


def safe_strip(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()


def safe_list(value: Any) -> list:
    if value is None:
        return []

    if isinstance(value, list):
        cleaned_items = []

        for item in value:
            if isinstance(item, dict):
                cleaned_items.append(str(item))
            else:
                cleaned_items.append(str(item).strip())

        return [item for item in cleaned_items if item]

    if isinstance(value, str):
        return [value.strip()] if value.strip() else []

    return [str(value).strip()]


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
    tags = safe_list(payload.get("tags", []))

    return {
        "raw_job_id": raw_job_id,
        "source_name": source_name,
        "external_job_id": safe_strip(external_job_id),
        "title": safe_strip(payload.get("title")),
        "company_name": safe_strip(payload.get("company_name")),
        "location": safe_strip(payload.get("candidate_required_location")),
        "job_type": safe_strip(payload.get("job_type")),
        "category": safe_strip(payload.get("category")),
        "tags": tags,
        "salary": safe_strip(payload.get("salary")),
        "job_url": safe_strip(payload.get("url")),
        "description": clean_html(payload.get("description", "")),
        "publication_date": parse_publication_date(payload.get("publication_date")),
    }


def normalize_arbeitnow_job(raw_job_id, source_name, external_job_id, payload):
    job_types = safe_list(payload.get("job_types", []))
    tags = safe_list(payload.get("tags", []))

    job_type = ", ".join(job_types)
    category = ", ".join(tags[:3])

    location = safe_strip(payload.get("location"))

    if payload.get("remote") is True:
        if location:
            location = f"Remote - {location}"
        else:
            location = "Remote"

    return {
        "raw_job_id": raw_job_id,
        "source_name": source_name,
        "external_job_id": safe_strip(external_job_id),
        "title": safe_strip(payload.get("title")),
        "company_name": safe_strip(payload.get("company_name")),
        "location": location,
        "job_type": job_type,
        "category": category,
        "tags": tags,
        "salary": "",
        "job_url": safe_strip(payload.get("url")),
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


def normalize_job_by_source(raw_job_id, source_name, external_job_id, payload):
    if source_name == "Remotive":
        return normalize_remotive_job(
            raw_job_id,
            source_name,
            external_job_id,
            payload,
        )

    if source_name == "Arbeitnow":
        return normalize_arbeitnow_job(
            raw_job_id,
            source_name,
            external_job_id,
            payload,
        )

    return None


def main():
    print("Starting job normalization...")

    conn = get_db_connection()

    try:
        raw_jobs = fetch_raw_jobs(conn)
        print(f"Raw jobs found: {len(raw_jobs)}")

        normalized_count = 0
        skipped_count = 0
        source_counts = {}

        for raw_job_id, source_name, external_job_id, payload in raw_jobs:
            normalized_job = normalize_job_by_source(
                raw_job_id,
                source_name,
                external_job_id,
                payload,
            )

            if normalized_job is None:
                print(f"Skipped unsupported source: {source_name}")
                skipped_count += 1
                continue

            if not normalized_job["title"] or not normalized_job["job_url"]:
                print(f"Skipped invalid job record. Raw job ID: {raw_job_id}")
                skipped_count += 1
                continue

            save_normalized_job(conn, normalized_job)
            normalized_count += 1

            source_counts[source_name] = source_counts.get(source_name, 0) + 1

            print(
                f"Normalized: {normalized_job['title']} "
                f"at {normalized_job['company_name']} "
                f"from {source_name}"
            )

        conn.commit()

        print("\nJob normalization completed.")
        print(f"Normalized jobs: {normalized_count}")
        print(f"Skipped jobs: {skipped_count}")

        print("\nSource-wise normalized count:")
        for source, count in sorted(source_counts.items()):
            print(f"- {source}: {count}")

    except Exception as error:
        conn.rollback()
        print("Job normalization failed.")
        print(error)

    finally:
        conn.close()


if __name__ == "__main__":
    main()