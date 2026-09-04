import os
import psycopg
from dotenv import load_dotenv

load_dotenv()


def view_normalized_jobs():
    conn = psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )

    query = """
        SELECT
            title,
            company_name,
            location,
            job_type,
            category,
            job_url,
            normalized_at
        FROM jobs_normalized
        ORDER BY normalized_at DESC
        LIMIT 10;
    """

    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()

        print("Latest normalized jobs:")
        print("-" * 100)

        for row in rows:
            print(f"Title: {row[0]}")
            print(f"Company: {row[1]}")
            print(f"Location: {row[2]}")
            print(f"Job Type: {row[3]}")
            print(f"Category: {row[4]}")
            print(f"URL: {row[5]}")
            print(f"Normalized At: {row[6]}")
            print("-" * 100)

    conn.close()


if __name__ == "__main__":
    view_normalized_jobs()