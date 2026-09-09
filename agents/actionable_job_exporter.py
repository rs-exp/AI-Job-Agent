import csv
import os
from datetime import datetime
from pathlib import Path

import psycopg
from dotenv import load_dotenv

load_dotenv()

SCORING_VERSION = "rule_v0.2"

BASE_DIR = Path(__file__).resolve().parent.parent
EXPORTS_DIR = BASE_DIR / "exports"

APPLY_TODAY_CSV = EXPORTS_DIR / "apply_today.csv"
APPLY_TODAY_MD = EXPORTS_DIR / "apply_today.md"
REVIEW_QUEUE_CSV = EXPORTS_DIR / "review_queue.csv"

APPLY_TODAY_LIMIT = 25
REVIEW_QUEUE_LIMIT = 100


def get_db_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def format_list(value):
    if value is None:
        return ""

    if isinstance(value, list):
        return ", ".join(str(item) for item in value)

    return str(value)


def fetch_actionable_jobs(conn, limit):
    query = """
        SELECT
            jad.normalized_job_id,
            jad.decision_status,
            jad.priority_score,
            jad.fit_bucket,
            j.source_name,
            j.title,
            j.company_name,
            j.location,
            j.job_type,
            j.category,
            j.job_url,
            js.role_score,
            js.skill_score,
            js.experience_score,
            js.location_score,
            js.penalty_score,
            js.matched_keywords,
            js.red_flags,
            jad.decision_reason,
            jad.recommendation,
            jad.user_notes,
            jad.updated_at
        FROM job_application_decisions jad
        JOIN jobs_normalized j
            ON jad.normalized_job_id = j.id
        JOIN job_scores js
            ON jad.normalized_job_id = js.normalized_job_id
            AND jad.scoring_version = js.scoring_version
        WHERE
            jad.scoring_version = %s
            AND jad.decision_status IN ('apply', 'review')
            AND COALESCE(j.is_duplicate, FALSE) = FALSE
        ORDER BY
            CASE jad.decision_status
                WHEN 'apply' THEN 1
                WHEN 'review' THEN 2
                ELSE 3
            END,
            jad.priority_score DESC,
            js.skill_score DESC,
            js.role_score DESC,
            j.source_name ASC
        LIMIT %s;
    """

    with conn.cursor() as cur:
        cur.execute(query, (SCORING_VERSION, limit))
        return cur.fetchall()


def fetch_review_queue(conn, limit):
    query = """
        SELECT
            jad.normalized_job_id,
            jad.decision_status,
            jad.priority_score,
            jad.fit_bucket,
            j.source_name,
            j.title,
            j.company_name,
            j.location,
            j.job_type,
            j.category,
            j.job_url,
            js.matched_keywords,
            js.red_flags,
            jad.decision_reason,
            jad.recommendation,
            jad.user_notes,
            jad.updated_at
        FROM job_application_decisions jad
        JOIN jobs_normalized j
            ON jad.normalized_job_id = j.id
        JOIN job_scores js
            ON jad.normalized_job_id = js.normalized_job_id
            AND jad.scoring_version = js.scoring_version
        WHERE
            jad.scoring_version = %s
            AND jad.decision_status IN ('review', 'save_for_later')
            AND COALESCE(j.is_duplicate, FALSE) = FALSE
        ORDER BY
            CASE jad.decision_status
                WHEN 'review' THEN 1
                WHEN 'save_for_later' THEN 2
                ELSE 3
            END,
            jad.priority_score DESC,
            js.skill_score DESC,
            js.role_score DESC
        LIMIT %s;
    """

    with conn.cursor() as cur:
        cur.execute(query, (SCORING_VERSION, limit))
        return cur.fetchall()


def write_apply_today_csv(rows):
    headers = [
        "rank",
        "job_id",
        "decision_status",
        "priority_score",
        "fit_bucket",
        "source_name",
        "title",
        "company_name",
        "location",
        "job_type",
        "category",
        "job_url",
        "role_score",
        "skill_score",
        "experience_score",
        "location_score",
        "penalty_score",
        "matched_keywords",
        "red_flags",
        "decision_reason",
        "recommendation",
        "user_notes",
        "updated_at",
    ]

    with open(APPLY_TODAY_CSV, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(headers)

        for index, row in enumerate(rows, start=1):
            row = list(row)
            row[16] = format_list(row[16])
            row[17] = format_list(row[17])
            writer.writerow([index] + row)


def write_review_queue_csv(rows):
    headers = [
        "rank",
        "job_id",
        "decision_status",
        "priority_score",
        "fit_bucket",
        "source_name",
        "title",
        "company_name",
        "location",
        "job_type",
        "category",
        "job_url",
        "matched_keywords",
        "red_flags",
        "decision_reason",
        "recommendation",
        "user_notes",
        "updated_at",
    ]

    with open(REVIEW_QUEUE_CSV, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(headers)

        for index, row in enumerate(rows, start=1):
            row = list(row)
            row[11] = format_list(row[11])
            row[12] = format_list(row[12])
            writer.writerow([index] + row)


def write_apply_today_markdown(rows):
    generated_at = datetime.now().isoformat(timespec="seconds")

    lines = []
    lines.append("# AI Job Agent - Apply Today")
    lines.append("")
    lines.append(f"Generated at: {generated_at}")
    lines.append(f"Scoring version: `{SCORING_VERSION}`")
    lines.append(f"Jobs included: `{len(rows)}`")
    lines.append("")
    lines.append("---")
    lines.append("")

    if not rows:
        lines.append("No apply/review jobs found.")
    else:
        for index, row in enumerate(rows, start=1):
            (
                job_id,
                decision_status,
                priority_score,
                fit_bucket,
                source_name,
                title,
                company_name,
                location,
                job_type,
                category,
                job_url,
                role_score,
                skill_score,
                experience_score,
                location_score,
                penalty_score,
                matched_keywords,
                red_flags,
                decision_reason,
                recommendation,
                user_notes,
                updated_at,
            ) = row

            lines.append(f"## {index}. {title}")
            lines.append("")
            lines.append(f"**Job ID:** {job_id}")
            lines.append(f"**Decision:** {decision_status}")
            lines.append(f"**Priority Score:** {priority_score}/100")
            lines.append(f"**Fit Bucket:** {fit_bucket}")
            lines.append(f"**Company:** {company_name}")
            lines.append(f"**Source:** {source_name}")
            lines.append(f"**Location:** {location}")
            lines.append(f"**Job Type:** {job_type}")
            lines.append(f"**Category:** {category}")
            lines.append("")
            lines.append("### Why this is here")
            lines.append("")
            lines.append(decision_reason or "")
            lines.append("")
            lines.append("### Recommendation")
            lines.append("")
            lines.append(recommendation or "")
            lines.append("")
            lines.append("### Match")
            lines.append("")
            lines.append(f"**Matched Keywords:** {format_list(matched_keywords)}")
            lines.append(f"**Red Flags:** {format_list(red_flags)}")
            lines.append("")
            lines.append("### Score Breakdown")
            lines.append("")
            lines.append(f"- Role Score: {role_score}/100")
            lines.append(f"- Skill Score: {skill_score}/100")
            lines.append(f"- Experience Score: {experience_score}/100")
            lines.append(f"- Location Score: {location_score}/100")
            lines.append(f"- Penalty Score: {penalty_score}")
            lines.append("")
            if user_notes:
                lines.append("### User Notes")
                lines.append("")
                lines.append(user_notes)
                lines.append("")
            lines.append(f"**Updated At:** {updated_at}")
            lines.append(f"**Job URL:** {job_url}")
            lines.append("")
            lines.append("---")
            lines.append("")

    with open(APPLY_TODAY_MD, "w", encoding="utf-8") as file:
        file.write("\n".join(lines))


def print_summary(apply_rows, review_rows):
    print("\nActionable export summary")
    print("-" * 100)
    print(f"Apply today rows: {len(apply_rows)}")
    print(f"Review queue rows: {len(review_rows)}")
    print(f"Apply today CSV: {APPLY_TODAY_CSV}")
    print(f"Apply today Markdown: {APPLY_TODAY_MD}")
    print(f"Review queue CSV: {REVIEW_QUEUE_CSV}")
    print("-" * 100)


def main():
    print("Starting actionable job export...")
    print(f"Scoring version: {SCORING_VERSION}")

    EXPORTS_DIR.mkdir(exist_ok=True)

    conn = get_db_connection()

    try:
        apply_rows = fetch_actionable_jobs(conn, APPLY_TODAY_LIMIT)
        review_rows = fetch_review_queue(conn, REVIEW_QUEUE_LIMIT)

        write_apply_today_csv(apply_rows)
        write_apply_today_markdown(apply_rows)
        write_review_queue_csv(review_rows)

        print_summary(apply_rows, review_rows)

    except Exception as error:
        print("Actionable job export failed.")
        print(error)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
