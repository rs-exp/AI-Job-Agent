import os
import psycopg
from dotenv import load_dotenv

load_dotenv()


def view_deduplication_summary():
    conn = psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )

    summary_query = """
        SELECT
            COUNT(*) AS total_jobs,
            COUNT(*) FILTER (WHERE is_duplicate = FALSE) AS unique_jobs,
            COUNT(*) FILTER (WHERE is_duplicate = TRUE) AS duplicate_jobs,
            COUNT(*) FILTER (WHERE dedupe_key IS NOT NULL) AS jobs_with_dedupe_key
        FROM jobs_normalized;
    """

    duplicate_query = """
        SELECT
            j.id,
            j.title,
            j.company_name,
            j.location,
            j.is_duplicate,
            j.duplicate_of_job_id,
            j.dedupe_reason
        FROM jobs_normalized j
        ORDER BY j.is_duplicate DESC, j.id ASC
        LIMIT 20;
    """

    with conn.cursor() as cur:
        cur.execute(summary_query)
        summary = cur.fetchone()

        print("Deduplication Summary")
        print("-" * 80)
        print(f"Total jobs: {summary[0]}")
        print(f"Unique jobs: {summary[1]}")
        print(f"Duplicate jobs: {summary[2]}")
        print(f"Jobs with dedupe key: {summary[3]}")
        print("-" * 80)

        cur.execute(duplicate_query)
        rows = cur.fetchall()

        print("\nSample deduplication records:")
        print("-" * 80)

        for row in rows:
            print(f"ID: {row[0]}")
            print(f"Title: {row[1]}")
            print(f"Company: {row[2]}")
            print(f"Location: {row[3]}")
            print(f"Is Duplicate: {row[4]}")
            print(f"Duplicate Of Job ID: {row[5]}")
            print(f"Reason: {row[6]}")
            print("-" * 80)

    conn.close()


if __name__ == "__main__":
    view_deduplication_summary()