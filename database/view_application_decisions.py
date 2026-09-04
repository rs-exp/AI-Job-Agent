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


def view_decision_summary(conn):
    query = """
        SELECT
            decision_status,
            COUNT(*) AS job_count
        FROM job_application_decisions
        WHERE scoring_version = %s
        GROUP BY decision_status
        ORDER BY job_count DESC;
    """

    with conn.cursor() as cur:
        cur.execute(query, (SCORING_VERSION,))
        rows = cur.fetchall()

        print("Application Decision Summary")
        print("-" * 100)

        for status, count in rows:
            print(f"{status}: {count}")

        print("-" * 100)


def view_top_decisions(conn):
    query = """
        SELECT
            jad.decision_status,
            jad.priority_score,
            jad.fit_bucket,
            j.source_name,
            j.title,
            j.company_name,
            j.location,
            j.job_url,
            jad.decision_reason,
            jad.recommendation
        FROM job_application_decisions jad
        JOIN jobs_normalized j
            ON jad.normalized_job_id = j.id
        WHERE jad.scoring_version = %s
        ORDER BY
            CASE jad.decision_status
                WHEN 'apply' THEN 1
                WHEN 'review' THEN 2
                WHEN 'save_for_later' THEN 3
                WHEN 'skip' THEN 4
                ELSE 5
            END,
            jad.priority_score DESC
        LIMIT 20;
    """

    with conn.cursor() as cur:
        cur.execute(query, (SCORING_VERSION,))
        rows = cur.fetchall()

        print("\nTop Application Decisions")
        print("-" * 100)

        for row in rows:
            print(f"Decision: {row[0]}")
            print(f"Priority Score: {row[1]}/100")
            print(f"Fit Bucket: {row[2]}")
            print(f"Source: {row[3]}")
            print(f"Title: {row[4]}")
            print(f"Company: {row[5]}")
            print(f"Location: {row[6]}")
            print(f"URL: {row[7]}")
            print(f"Decision Reason: {row[8]}")
            print(f"Recommendation: {row[9]}")
            print("-" * 100)


def main():
    conn = get_db_connection()

    try:
        view_decision_summary(conn)
        view_top_decisions(conn)

    finally:
        conn.close()


if __name__ == "__main__":
    main()