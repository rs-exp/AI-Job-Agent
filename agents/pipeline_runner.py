import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

import psycopg
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


PIPELINE_STEPS = [
    {
        "name": "Source Access Check",
        "script": "agents/source_checker_db.py",
    },
    {
        "name": "Remotive Raw Job Ingestion",
        "script": "agents/remotive_ingestor.py",
    },
    {
        "name": "Arbeitnow Raw Job Ingestion",
        "script": "agents/arbeitnow_ingestor.py",
    },
    {
        "name": "Job Normalization",
        "script": "agents/job_normalizer.py",
    },
    {
        "name": "Job Deduplication",
        "script": "agents/job_deduplicator.py",
    },
    {
        "name": "Job Match Scoring",
        "script": "agents/job_match_scorer.py",
    },
    {
        "name": "Application Decision Generation",
        "script": "agents/application_decision_generator.py",
    },
    {
        "name": "Top Job Report Generation",
        "script": "agents/job_report_generator.py",
    },
    {
        "name": "Actionable Job Export",
        "script": "agents/actionable_job_exporter.py",
    },
    {
        "name": "Application Message Generation",
        "script": "agents/application_message_generator.py",
    },
    {
        "name": "Resume Tailoring Pack Generation",
        "script": "agents/resume_tailoring_pack_generator.py",
    },
]


def get_db_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def create_pipeline_run(conn, run_name):
    query = """
        INSERT INTO pipeline_runs (
            run_name,
            status,
            started_at
        )
        VALUES (%s, %s, %s)
        RETURNING id;
    """

    with conn.cursor() as cur:
        cur.execute(query, (run_name, "started", datetime.now()))
        return cur.fetchone()[0]


def get_pipeline_counts(conn):
    counts = {
        "total_raw_jobs": 0,
        "total_normalized_jobs": 0,
        "total_unique_jobs": 0,
        "total_duplicate_jobs": 0,
        "total_scored_jobs": 0,
    }

    queries = {
        "total_raw_jobs": "SELECT COUNT(*) FROM jobs_raw;",
        "total_normalized_jobs": "SELECT COUNT(*) FROM jobs_normalized;",
        "total_unique_jobs": """
            SELECT COUNT(*)
            FROM jobs_normalized
            WHERE COALESCE(is_duplicate, FALSE) = FALSE;
        """,
        "total_duplicate_jobs": """
            SELECT COUNT(*)
            FROM jobs_normalized
            WHERE COALESCE(is_duplicate, FALSE) = TRUE;
        """,
        "total_scored_jobs": "SELECT COUNT(*) FROM job_scores;",
    }

    with conn.cursor() as cur:
        for key, query in queries.items():
            cur.execute(query)
            counts[key] = cur.fetchone()[0]

    return counts


def update_pipeline_run(conn, run_id, status, counts=None, error_message=None):
    counts = counts or {}

    query = """
        UPDATE pipeline_runs
        SET
            status = %s,
            finished_at = %s,
            total_raw_jobs = %s,
            total_normalized_jobs = %s,
            total_unique_jobs = %s,
            total_duplicate_jobs = %s,
            total_scored_jobs = %s,
            error_message = %s
        WHERE id = %s;
    """

    with conn.cursor() as cur:
        cur.execute(
            query,
            (
                status,
                datetime.now(),
                counts.get("total_raw_jobs", 0),
                counts.get("total_normalized_jobs", 0),
                counts.get("total_unique_jobs", 0),
                counts.get("total_duplicate_jobs", 0),
                counts.get("total_scored_jobs", 0),
                error_message,
                run_id,
            ),
        )


def run_script(step_name, script_relative_path):
    script_path = BASE_DIR / script_relative_path

    print("=" * 100)
    print(f"Running step: {step_name}")
    print(f"Script: {script_relative_path}")
    print("=" * 100)

    if not script_path.exists():
        raise FileNotFoundError(f"Script not found: {script_path}")

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
    )

    if result.stdout:
        print(result.stdout)

    if result.stderr:
        print("STDERR:")
        print(result.stderr)

    if result.returncode != 0:
        raise RuntimeError(
            f"Step failed: {step_name}. Return code: {result.returncode}"
        )

    print(f"Step completed: {step_name}")
    print()


def main():
    run_name = "daily_job_pipeline_v0.1"

    print("Starting AI Job Agent pipeline...")
    print(f"Project directory: {BASE_DIR}")

    conn = get_db_connection()
    run_id = None

    try:
        run_id = create_pipeline_run(conn, run_name)
        conn.commit()

        print(f"Pipeline run created. Run ID: {run_id}")

        for step in PIPELINE_STEPS:
            run_script(step["name"], step["script"])

        counts = get_pipeline_counts(conn)

        update_pipeline_run(
            conn=conn,
            run_id=run_id,
            status="completed",
            counts=counts,
            error_message=None,
        )

        conn.commit()

        print("=" * 100)
        print("AI Job Agent pipeline completed successfully.")
        print("=" * 100)
        print(f"Raw jobs: {counts['total_raw_jobs']}")
        print(f"Normalized jobs: {counts['total_normalized_jobs']}")
        print(f"Unique jobs: {counts['total_unique_jobs']}")
        print(f"Duplicate jobs: {counts['total_duplicate_jobs']}")
        print(f"Scored jobs: {counts['total_scored_jobs']}")

    except Exception as error:
        conn.rollback()

        error_message = str(error)

        if run_id is not None:
            try:
                counts = get_pipeline_counts(conn)

                update_pipeline_run(
                    conn=conn,
                    run_id=run_id,
                    status="failed",
                    counts=counts,
                    error_message=error_message,
                )

                conn.commit()

            except Exception:
                conn.rollback()

        print("=" * 100)
        print("AI Job Agent pipeline failed.")
        print("=" * 100)
        print(error_message)

    finally:
        conn.close()


if __name__ == "__main__":
    main()