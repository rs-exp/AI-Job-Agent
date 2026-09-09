import os
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


def print_rows(title, rows):
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)

    if not rows:
        print("No rows found.")
        return

    for row in rows:
        print(row)


def main():
    conn = get_db_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT source_name, COUNT(*)
                FROM jobs_raw
                GROUP BY source_name
                ORDER BY source_name;
            """)
            print_rows("RAW JOBS BY SOURCE", cur.fetchall())

            cur.execute("""
                SELECT source_name, COUNT(*)
                FROM jobs_normalized
                GROUP BY source_name
                ORDER BY source_name;
            """)
            print_rows("NORMALIZED JOBS BY SOURCE", cur.fetchall())

            cur.execute("""
                SELECT
                    jad.decision_status,
                    COUNT(*)
                FROM job_application_decisions jad
                JOIN jobs_normalized j
                    ON jad.normalized_job_id = j.id
                WHERE
                    j.source_name = 'ManualSweep'
                    AND jad.scoring_version = 'rule_v0.2'
                GROUP BY jad.decision_status
                ORDER BY COUNT(*) DESC;
            """)
            print_rows("MANUALSWEEP DECISIONS", cur.fetchall())

            cur.execute("""
                SELECT
                    js.overall_score,
                    js.fit_bucket,
                    j.title,
                    j.company_name,
                    j.location,
                    js.matched_keywords,
                    js.red_flags
                FROM job_scores js
                JOIN jobs_normalized j
                    ON js.normalized_job_id = j.id
                WHERE
                    j.source_name = 'ManualSweep'
                    AND js.scoring_version = 'rule_v0.2'
                ORDER BY
                    js.overall_score DESC,
                    js.skill_score DESC,
                    js.role_score DESC
                LIMIT 20;
            """)
            print_rows("TOP MANUALSWEEP JOBS BY SCORE", cur.fetchall())

            cur.execute("""
                SELECT
                    j.source_name,
                    jad.decision_status,
                    COUNT(*)
                FROM job_application_decisions jad
                JOIN jobs_normalized j
                    ON jad.normalized_job_id = j.id
                WHERE jad.scoring_version = 'rule_v0.2'
                GROUP BY j.source_name, jad.decision_status
                ORDER BY j.source_name, jad.decision_status;
            """)
            print_rows("ALL DECISIONS BY SOURCE", cur.fetchall())

    finally:
        conn.close()


if __name__ == "__main__":
    main()