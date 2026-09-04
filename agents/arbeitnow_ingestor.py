import os
import requests
import psycopg
from psycopg.types.json import Jsonb
from dotenv import load_dotenv

load_dotenv()

ARBEITNOW_API_URL = "https://www.arbeitnow.com/api/job-board-api?page=1"
MAX_JOBS_TO_SAVE = 20

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


def fetch_arbeitnow_jobs():
    response = requests.get(
        ARBEITNOW_API_URL,
        headers=HEADERS,
        timeout=20,
    )

    response.raise_for_status()

    data = response.json()
    jobs = data.get("data", [])

    return jobs[:MAX_JOBS_TO_SAVE]


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
            external_job_id = EXCLUDED.external_job_id,
            job_title = EXCLUDED.job_title,
            company_name = EXCLUDED.company_name,
            raw_payload = EXCLUDED.raw_payload,
            fetched_at = CURRENT_TIMESTAMP;
    """

    with conn.cursor() as cur:
        cur.execute(
            query,
            (
                "Arbeitnow",
                str(job.get("slug", "")),
                job.get("title", ""),
                job.get("company_name", ""),
                job.get("url", ""),
                Jsonb(job),
            ),
        )


def main():
    print("Starting Arbeitnow job ingestion...")

    try:
        jobs = fetch_arbeitnow_jobs()
        print(f"Jobs fetched from Arbeitnow: {len(jobs)}")

        if not jobs:
            print("No jobs returned from Arbeitnow.")
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
            print("\nArbeitnow job ingestion completed.")
            print("Raw jobs saved to PostgreSQL.")

        except Exception as error:
            conn.rollback()
            print("Failed while saving Arbeitnow jobs to database.")
            print(error)

        finally:
            conn.close()

    except requests.exceptions.RequestException as error:
        print("Failed to fetch jobs from Arbeitnow.")
        print(error)

    except Exception as error:
        print("Unexpected error.")
        print(error)


if __name__ == "__main__":
    main()