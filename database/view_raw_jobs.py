import os
import psycopg
from dotenv import load_dotenv

load_dotenv()


def view_raw_jobs():
    conn = psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )

    query = """
        SELECT
            source_name,
            job_title,
            company_name,
            job_url,
            fetched_at
        FROM jobs_raw
        ORDER BY fetched_at DESC
        LIMIT 10;
    """

    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()

        print("Latest raw jobs:")
        print("-" * 100)

        for row in rows:
            print(f"Source: {row[0]}")
            print(f"Title: {row[1]}")
            print(f"Company: {row[2]}")
            print(f"URL: {row[3]}")
            print(f"Fetched At: {row[4]}")
            print("-" * 100)

    conn.close()


if __name__ == "__main__":
    view_raw_jobs()