import os
import psycopg
from dotenv import load_dotenv

load_dotenv()


def view_pipeline_runs():
    conn = psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )

    query = """
        SELECT
            id,
            run_name,
            status,
            started_at,
            finished_at,
            total_raw_jobs,
            total_normalized_jobs,
            total_unique_jobs,
            total_duplicate_jobs,
            total_scored_jobs,
            error_message
        FROM pipeline_runs
        ORDER BY started_at DESC
        LIMIT 10;
    """

    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()

        print("Latest pipeline runs:")
        print("-" * 100)

        for row in rows:
            print(f"Run ID: {row[0]}")
            print(f"Run Name: {row[1]}")
            print(f"Status: {row[2]}")
            print(f"Started At: {row[3]}")
            print(f"Finished At: {row[4]}")
            print(f"Raw Jobs: {row[5]}")
            print(f"Normalized Jobs: {row[6]}")
            print(f"Unique Jobs: {row[7]}")
            print(f"Duplicate Jobs: {row[8]}")
            print(f"Scored Jobs: {row[9]}")
            print(f"Error: {row[10]}")
            print("-" * 100)

    conn.close()


if __name__ == "__main__":
    view_pipeline_runs()