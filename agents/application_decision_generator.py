import os
import re
from datetime import datetime

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


def normalize_text(value):
    if value is None:
        return ""

    value = str(value).lower()
    value = re.sub(r"[^a-z0-9\s/-]", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def fetch_scored_jobs(conn):
    query = """
        SELECT
            j.id AS normalized_job_id,
            j.title,
            j.company_name,
            j.location,
            j.source_name,
            j.job_type,
            j.category,
            j.tags,
            j.description,
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


def detect_applied_from_manual_sweep(
    source_name,
    job_type,
    category,
    tags,
    description,
):
    if source_name != "ManualSweep":
        return False, None

    tags_text = " ".join(tags or []) if isinstance(tags, list) else str(tags or "")

    combined_text = normalize_text(
        " ".join(
            [
                job_type or "",
                category or "",
                tags_text,
                description or "",
            ]
        )
    )

    applied_patterns = [
        "applied",
        "indeed applied",
        "linkedin applied",
        "naukri applied",
        "applied 03-sep",
        "applied 04-sep",
        "applied 05-sep",
        "applied 06-sep",
        "applied 07-sep",
        "applied 08-sep",
        "applied 09-sep",
    ]

    for pattern in applied_patterns:
        if pattern in combined_text:
            applied_at = extract_applied_date(combined_text)
            return True, applied_at

    return False, None


def extract_applied_date(text):
    month_map = {
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "sept": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
    }

    match = re.search(
        r"applied\s+(\d{1,2})[-\s/]([a-z]{3,4})",
        text,
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    day = int(match.group(1))
    month_name = match.group(2).lower()
    month = month_map.get(month_name)

    if not month:
        return None

    try:
        return datetime(datetime.now().year, month, day)
    except ValueError:
        return None


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
    manual_override=False,
    manual_override_reason=None,
    applied_at=None,
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
            manual_override_reason,
            applied_at,
            updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
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

            recommendation =
                CASE
                    WHEN job_application_decisions.decision_status = 'applied'
                    THEN job_application_decisions.recommendation

                    WHEN COALESCE(job_application_decisions.manual_override, FALSE) = TRUE
                    THEN job_application_decisions.recommendation

                    ELSE EXCLUDED.recommendation
                END,

            manual_override =
                CASE
                    WHEN EXCLUDED.decision_status = 'applied'
                    THEN TRUE

                    WHEN COALESCE(job_application_decisions.manual_override, FALSE) = TRUE
                    THEN TRUE

                    ELSE job_application_decisions.manual_override
                END,

            manual_override_reason =
                CASE
                    WHEN EXCLUDED.decision_status = 'applied'
                    THEN EXCLUDED.manual_override_reason

                    WHEN COALESCE(job_application_decisions.manual_override, FALSE) = TRUE
                    THEN job_application_decisions.manual_override_reason

                    ELSE job_application_decisions.manual_override_reason
                END,

            applied_at =
                CASE
                    WHEN job_application_decisions.decision_status = 'applied'
                    THEN COALESCE(job_application_decisions.applied_at, EXCLUDED.applied_at, CURRENT_TIMESTAMP)

                    WHEN EXCLUDED.decision_status = 'applied'
                    THEN COALESCE(EXCLUDED.applied_at, CURRENT_TIMESTAMP)

                    ELSE job_application_decisions.applied_at
                END,

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
                manual_override,
                manual_override_reason,
                applied_at,
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
                job_type,
                category,
                tags,
                description,
                overall_score,
                fit_bucket,
                recommendation,
                red_flags,
            ) = job

            already_applied, applied_at = detect_applied_from_manual_sweep(
                source_name=source_name,
                job_type=job_type,
                category=category,
                tags=tags,
                description=description,
            )

            if already_applied:
                decision_status = "applied"
                decision_reason = (
                    "Marked as already applied because imported ManualSweep data "
                    "contains applied status."
                )
                recommendation_to_save = (
                    "No action needed. This job was already applied according to "
                    "the imported manual sweep/status data."
                )
                manual_override = True
                manual_override_reason = "Auto-locked from ManualSweep applied status."
            else:
                decision_status, decision_reason = decide_status(
                    overall_score,
                    fit_bucket,
                    red_flags,
                )
                recommendation_to_save = recommendation
                manual_override = False
                manual_override_reason = None

            save_application_decision(
                conn=conn,
                normalized_job_id=normalized_job_id,
                decision_status=decision_status,
                priority_score=overall_score,
                fit_bucket=fit_bucket,
                decision_reason=decision_reason,
                recommendation=recommendation_to_save,
                manual_override=manual_override,
                manual_override_reason=manual_override_reason,
                applied_at=applied_at,
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