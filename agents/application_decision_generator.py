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


def fetch_scored_jobs(conn):
    query = """
        SELECT
            j.id AS normalized_job_id,
            j.title,
            j.company_name,
            j.location,
            j.source_name,
            js.overall_score,
            js.fit_bucket,
            js.recommendation,
            js.red_flags
        FROM job_scores js
        JOIN jobs_normalized j
            ON js.normalized_job_id = j.id
        WHERE
            js.scoring_version = %s
            AND COALESCE(j.is_duplicate, FALSE) = FALSE
        ORDER BY
            js.overall_score DESC,
            js.skill_score DESC,
            js.role_score DESC;
    """

    with conn.cursor() as cur:
        cur.execute(query, (SCORING_VERSION,))
        return cur.fetchall()


def decide_status(overall_score, fit_bucket, red_flags):
    red_flags = red_flags or []

    severe_flags = {
        "copywriter",
        "writer",
        "sales",
        "marketing",
        "business development",
        "intern",
        "student",
        "working student",
    }

    if any(flag in severe_flags for flag in red_flags):
        return "skip", "Skipped because severe non-target role/domain red flags were detected."

    if fit_bucket == "Strong Match" and overall_score >= 75:
        return "apply", "Strong score and fit bucket. Prioritize this job for application."

    if fit_bucket == "Good Match" and overall_score >= 55:
        return "review", "Good alignment. Review manually and tailor resume before applying."

    if fit_bucket == "Weak Match" and overall_score >= 35:
        return "save_for_later", "Weak alignment. Keep for later review only if pipeline has few better matches."

    return "skip", "Low score or poor fit for current Cloud/DevOps/SRE transition target."


def save_application_decision(
    conn,
    normalized_job_id,
    decision_status,
    priority_score,
    fit_bucket,
    decision_reason,
    recommendation,
):
    query = """
        INSERT INTO job_application_decisions (
            normalized_job_id,
            scoring_version,
            decision_status,
            priority_score,
            fit_bucket,
            decision_reason,
            recommendation,
            manual_override,
            updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, FALSE, CURRENT_TIMESTAMP)
        ON CONFLICT (normalized_job_id, scoring_version)
        DO UPDATE SET
            decision_status =
                CASE
                    WHEN job_application_decisions.decision_status = 'applied'
                    THEN job_application_decisions.decision_status

                    WHEN COALESCE(job_application_decisions.manual_override, FALSE) = TRUE
                    THEN job_application_decisions.decision_status

                    ELSE EXCLUDED.decision_status
                END,

            priority_score = EXCLUDED.priority_score,
            fit_bucket = EXCLUDED.fit_bucket,

            decision_reason =
                CASE
                    WHEN job_application_decisions.decision_status = 'applied'
                    THEN job_application_decisions.decision_reason

                    WHEN COALESCE(job_application_decisions.manual_override, FALSE) = TRUE
                    THEN job_application_decisions.decision_reason

                    ELSE EXCLUDED.decision_reason
                END,

            recommendation = EXCLUDED.recommendation,
            updated_at = CURRENT_TIMESTAMP;
    """

    with conn.cursor() as cur:
        cur.execute(
            query,
            (
                normalized_job_id,
                SCORING_VERSION,
                decision_status,
                priority_score,
                fit_bucket,
                decision_reason,
                recommendation,
            ),
        )


def main():
    print("Starting application decision generation...")
    print(f"Scoring version: {SCORING_VERSION}")

    conn = get_db_connection()

    try:
        scored_jobs = fetch_scored_jobs(conn)
        print(f"Scored jobs found: {len(scored_jobs)}")

        status_counts = {}

        for job in scored_jobs:
            (
                normalized_job_id,
                title,
                company_name,
                location,
                source_name,
                overall_score,
                fit_bucket,
                recommendation,
                red_flags,
            ) = job

            decision_status, decision_reason = decide_status(
                overall_score,
                fit_bucket,
                red_flags,
            )

            save_application_decision(
                conn=conn,
                normalized_job_id=normalized_job_id,
                decision_status=decision_status,
                priority_score=overall_score,
                fit_bucket=fit_bucket,
                decision_reason=decision_reason,
                recommendation=recommendation,
            )

            status_counts[decision_status] = status_counts.get(decision_status, 0) + 1

            print(
                f"{decision_status.upper()}: "
                f"{overall_score}/100 | "
                f"{title} at {company_name} | "
                f"{source_name} | {location}"
            )

        conn.commit()

        print("\nApplication decision generation completed.")
        print("Decision summary:")

        for status, count in sorted(status_counts.items()):
            print(f"- {status}: {count}")

        print("\nManual override protection is active.")
        print("Existing manual decisions and applied jobs will not be overwritten.")

    except Exception as error:
        conn.rollback()
        print("Application decision generation failed.")
        print(error)

    finally:
        conn.close()


if __name__ == "__main__":
    main()