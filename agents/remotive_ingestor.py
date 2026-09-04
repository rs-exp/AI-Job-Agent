import os
import requests
import psycopg
from psycopg.types.json import Jsonb
from dotenv import load_dotenv

load_dotenv()

REMOTIVE_API_URL = "https://remotive.com/api/remote-jobs?limit=10"

HEADERS = {
    "User-Agent": "AI-Job-Agent-Learning-Project/0.1"
}


def get_db_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def fetch_remotive_jobs():
    response = requests.get(
        REMOTIVE_API_URL,
        headers=HEADERS,
        timeout=20
    )

    response.raise_for_status()

    data = response.json()
    return data.get("jobs", [])


def save_raw_job(conn, job):
    query = """
        INSERT INTO jobs_raw (
            source_name,
            external_job_id,
            job_title,
            company_name,
            job_url,
            raw_payload
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (job_url)
        DO UPDATE SET
            job_title = EXCLUDED.job_title,
            company_name = EXCLUDED.company_name,
            raw_payload = EXCLUDED.raw_payload,
            fetched_at = CURRENT_TIMESTAMP;
    """

    with conn.cursor() as cur:
        cur.execute(
            query,
            (
                "Remotive",
                str(job.get("id", "")),
                job.get("title", ""),
                job.get("company_name", ""),
                job.get("url", ""),
                Jsonb(job),
            ),
        )


def main():
    print("Starting Remotive job ingestion...")

    try:
        jobs = fetch_remotive_jobs()
        print(f"Jobs fetched from Remotive: {len(jobs)}")

        if not jobs:
            print("No jobs returned from Remotive.")
            return

        conn = get_db_connection()

        try:
            for job in jobs:
                save_raw_job(conn, job)
                print(
                    f"Saved: {job.get('title', '')} "
                    f"at {job.get('company_name', '')}"
                )

            conn.commit()
            print("\nRemotive job ingestion completed.")
            print("Raw jobs saved to PostgreSQL.")

        except Exception as error:
            conn.rollback()
            print("Failed while saving jobs to database.")
            print(error)

        finally:
            conn.close()

    except requests.exceptions.RequestException as error:
        print("Failed to fetch jobs from Remotive.")
        print(error)

    except Exception as error:
        print("Unexpected error.")
        print(error)


if __name__ == "__main__":
    main()