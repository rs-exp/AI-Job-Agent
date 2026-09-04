import os
import re
import hashlib
import psycopg
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


def normalize_text(value):
    if not value:
        return ""

    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def build_dedupe_key(title, company_name, location):
    normalized_title = normalize_text(title)
    normalized_company = normalize_text(company_name)
    normalized_location = normalize_text(location)

    fingerprint_source = "|".join(
        [
            normalized_title,
            normalized_company,
            normalized_location,
        ]
    )

    return hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest()


def fetch_normalized_jobs(conn):
    query = """
        SELECT
            id,
            title,
            company_name,
            location,
            job_url
        FROM jobs_normalized
        ORDER BY id ASC;
    """

    with conn.cursor() as cur:
        cur.execute(query)
        return cur.fetchall()


def update_deduplication_status(
    conn,
    job_id,
    dedupe_key,
    is_duplicate,
    duplicate_of_job_id,
    dedupe_reason,
):
    query = """
        UPDATE jobs_normalized
        SET
            dedupe_key = %s,
            is_duplicate = %s,
            duplicate_of_job_id = %s,
            dedupe_reason = %s,
            deduped_at = CURRENT_TIMESTAMP
        WHERE id = %s;
    """

    with conn.cursor() as cur:
        cur.execute(
            query,
            (
                dedupe_key,
                is_duplicate,
                duplicate_of_job_id,
                dedupe_reason,
                job_id,
            ),
        )


def run_deduplication():
    print("Starting job deduplication...")

    conn = get_db_connection()

    try:
        jobs = fetch_normalized_jobs(conn)

        print(f"Normalized jobs found: {len(jobs)}")

        seen_jobs = {}
        unique_count = 0
        duplicate_count = 0

        for job_id, title, company_name, location, job_url in jobs:
            dedupe_key = build_dedupe_key(title, company_name, location)

            if dedupe_key in seen_jobs:
                canonical_job_id = seen_jobs[dedupe_key]

                update_deduplication_status(
                    conn=conn,
                    job_id=job_id,
                    dedupe_key=dedupe_key,
                    is_duplicate=True,
                    duplicate_of_job_id=canonical_job_id,
                    dedupe_reason="Duplicate based on title + company + location",
                )

                duplicate_count += 1

                print(
                    f"Duplicate: {title} at {company_name} "
                    f"-> duplicate of job ID {canonical_job_id}"
                )

            else:
                seen_jobs[dedupe_key] = job_id

                update_deduplication_status(
                    conn=conn,
                    job_id=job_id,
                    dedupe_key=dedupe_key,
                    is_duplicate=False,
                    duplicate_of_job_id=None,
                    dedupe_reason="Canonical job record",
                )

                unique_count += 1

                print(f"Unique: {title} at {company_name}")

        conn.commit()

        print("\nJob deduplication completed.")
        print(f"Unique jobs: {unique_count}")
        print(f"Duplicate jobs: {duplicate_count}")

    except Exception as error:
        conn.rollback()
        print("Job deduplication failed.")
        print(error)

    finally:
        conn.close()


if __name__ == "__main__":
    run_deduplication()