import os

import psycopg
from dotenv import load_dotenv

load_dotenv()

SCORING_VERSION = "rule_v0.2"


def get_db_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def main():
    conn = get_db_connection()

    query = """
        SELECT
            jad.normalized_job_id,
            jad.priority_score,
            jad.fit_bucket,
            j.source_name,
            j.title,
            j.company_name,
            j.location,
            j.category,
            j.job_url,
            jad.manual_override,
            jad.manual_override_reason,
            jad.decision_reason,
            jad.applied_at,
            jad.updated_at
        FROM job_application_decisions jad
        JOIN jobs_normalized j
            ON jad.normalized_job_id = j.id
        WHERE
            jad.scoring_version = %s
            AND jad.decision_status = 'applied'
        ORDER BY
            jad.applied_at DESC NULLS LAST,
            jad.updated_at DESC,
            jad.priority_score DESC;
    """

    try:
        with conn.cursor() as cur:
            cur.execute(query, (SCORING_VERSION,))
            rows = cur.fetchall()

        print("Applied Jobs")
        print("-" * 100)
        print(f"Total applied jobs: {len(rows)}")
        print("-" * 100)

        for row in rows:
            print(f"Job ID: {row[0]}")
            print(f"Priority Score: {row[1]}/100")
            print(f"Fit Bucket: {row[2]}")
            print(f"Source: {row[3]}")
            print(f"Title: {row[4]}")
            print(f"Company: {row[5]}")
            print(f"Location: {row[6]}")
            print(f"Category: {row[7]}")
            print(f"URL: {row[8]}")
            print(f"Manual Override: {row[9]}")
            print(f"Manual Override Reason: {row[10]}")
            print(f"Decision Reason: {row[11]}")
            print(f"Applied At: {row[12]}")
            print(f"Updated At: {row[13]}")
            print("-" * 100)

    finally:
        conn.close()


if __name__ == "__main__":
    main()