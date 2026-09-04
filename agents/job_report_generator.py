import csv
import os
from datetime import datetime
from pathlib import Path

import psycopg
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BASE_DIR / "reports"
MARKDOWN_REPORT = REPORTS_DIR / "top_jobs_report.md"
CSV_REPORT = REPORTS_DIR / "top_jobs_report.csv"

SCORING_VERSION = "rule_v0.2"
LIMIT = 40

REPORT_STATUSES = [
    "apply",
    "review",
    "save_for_later",
]


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


def fetch_decision_summary(conn):
    query = """
        SELECT
            decision_status,
            COUNT(*) AS job_count
        FROM job_application_decisions
        WHERE scoring_version = %s
        GROUP BY decision_status
        ORDER BY
            CASE decision_status
                WHEN 'apply' THEN 1
                WHEN 'review' THEN 2
                WHEN 'save_for_later' THEN 3
                WHEN 'skip' THEN 4
                WHEN 'applied' THEN 5
                ELSE 6
            END;
    """

    with conn.cursor() as cur:
        cur.execute(query, (SCORING_VERSION,))
        return cur.fetchall()


def fetch_report_jobs(conn):
    query = """
        SELECT
            jad.decision_status,
            jad.priority_score,
            jad.fit_bucket,
            jad.decision_reason,
            jad.recommendation,
            js.overall_score,
            js.role_score,
            js.skill_score,
            js.experience_score,
            js.location_score,
            js.penalty_score,
            js.matched_keywords,
            js.red_flags,
            js.score_summary,
            j.source_name,
            j.title,
            j.company_name,
            j.location,
            j.job_type,
            j.category,
            j.job_url,
            jad.updated_at
        FROM job_application_decisions jad
        JOIN job_scores js
            ON jad.normalized_job_id = js.normalized_job_id
            AND jad.scoring_version = js.scoring_version
        JOIN jobs_normalized j
            ON jad.normalized_job_id = j.id
        WHERE
            jad.scoring_version = %s
            AND COALESCE(j.is_duplicate, FALSE) = FALSE
            AND jad.decision_status = ANY(%s)
        ORDER BY
            CASE jad.decision_status
                WHEN 'apply' THEN 1
                WHEN 'review' THEN 2
                WHEN 'save_for_later' THEN 3
                ELSE 4
            END,
            jad.priority_score DESC,
            js.skill_score DESC,
            js.role_score DESC
        LIMIT %s;
    """

    with conn.cursor() as cur:
        cur.execute(
            query,
            (
                SCORING_VERSION,
                REPORT_STATUSES,
                LIMIT,
            ),
        )
        return cur.fetchall()


def write_markdown_report(rows, decision_summary):
    generated_at = datetime.now().isoformat(timespec="seconds")

    lines = []
    lines.append("# AI Job Agent - Application Decision Report")
    lines.append("")
    lines.append(f"Generated at: {generated_at}")
    lines.append(f"Scoring version: `{SCORING_VERSION}`")
    lines.append(f"Jobs included in report: `{len(rows)}`")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## Decision Summary")
    lines.append("")

    if decision_summary:
        lines.append("| Decision Status | Job Count |")
        lines.append("|---|---:|")

        for status, count in decision_summary:
            lines.append(f"| {status} | {count} |")
    else:
        lines.append("No application decisions found.")

    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## Actionable Jobs")
    lines.append("")

    if not rows:
        lines.append("No actionable jobs found. Run the full pipeline again after adding better sources.")
    else:
        for index, row in enumerate(rows, start=1):
            (
                decision_status,
                priority_score,
                fit_bucket,
                decision_reason,
                recommendation,
                overall_score,
                role_score,
                skill_score,
                experience_score,
                location_score,
                penalty_score,
                matched_keywords,
                red_flags,
                score_summary,
                source_name,
                title,
                company_name,
                location,
                job_type,
                category,
                job_url,
                updated_at,
            ) = row

            lines.append(f"## {index}. {title}")
            lines.append("")
            lines.append(f"**Decision:** {decision_status}")
            lines.append(f"**Priority Score:** {priority_score}/100")
            lines.append(f"**Fit Bucket:** {fit_bucket}")
            lines.append(f"**Company:** {company_name}")
            lines.append(f"**Source:** {source_name}")
            lines.append(f"**Location:** {location}")
            lines.append(f"**Job Type:** {job_type}")
            lines.append(f"**Category:** {category}")
            lines.append("")

            lines.append("### Decision Reason")
            lines.append("")
            lines.append(decision_reason or "")
            lines.append("")

            lines.append("### Recommendation")
            lines.append("")
            lines.append(recommendation or "")
            lines.append("")

            lines.append("### Score Breakdown")
            lines.append("")
            lines.append(f"- Overall Score: {overall_score}/100")
            lines.append(f"- Role Score: {role_score}/100")
            lines.append(f"- Skill Score: {skill_score}/100")
            lines.append(f"- Experience Score: {experience_score}/100")
            lines.append(f"- Location Score: {location_score}/100")
            lines.append(f"- Penalty Score: {penalty_score}")
            lines.append("")

            lines.append("### Match Details")
            lines.append("")
            lines.append(f"**Matched Keywords:** {format_list(matched_keywords)}")
            lines.append(f"**Red Flags:** {format_list(red_flags)}")
            lines.append("")

            lines.append("### Score Summary")
            lines.append("")
            lines.append(score_summary or "")
            lines.append("")
            lines.append(f"**Decision Updated At:** {updated_at}")
            lines.append(f"**Job URL:** {job_url}")
            lines.append("")
            lines.append("---")
            lines.append("")

    with open(MARKDOWN_REPORT, "w", encoding="utf-8") as file:
        file.write("\n".join(lines))


def write_csv_report(rows):
    fieldnames = [
        "decision_status",
        "priority_score",
        "fit_bucket",
        "decision_reason",
        "recommendation",
        "overall_score",
        "role_score",
        "skill_score",
        "experience_score",
        "location_score",
        "penalty_score",
        "matched_keywords",
        "red_flags",
        "score_summary",
        "source_name",
        "title",
        "company_name",
        "location",
        "job_type",
        "category",
        "job_url",
        "decision_updated_at",
    ]

    with open(CSV_REPORT, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(fieldnames)

        for row in rows:
            row = list(row)
            row[11] = format_list(row[11])
            row[12] = format_list(row[12])
            writer.writerow(row)


def main():
    print("Starting decision-aware job report generation...")
    print(f"Scoring version: {SCORING_VERSION}")

    REPORTS_DIR.mkdir(exist_ok=True)

    conn = get_db_connection()

    try:
        decision_summary = fetch_decision_summary(conn)
        rows = fetch_report_jobs(conn)

        print(f"Decision groups found: {len(decision_summary)}")
        print(f"Actionable jobs fetched: {len(rows)}")

        write_markdown_report(rows, decision_summary)
        write_csv_report(rows)

        print("Report generation completed.")
        print(f"Markdown report: {MARKDOWN_REPORT}")
        print(f"CSV report: {CSV_REPORT}")

    except Exception as error:
        print("Report generation failed.")
        print(error)

    finally:
        conn.close()


if __name__ == "__main__":
    main()