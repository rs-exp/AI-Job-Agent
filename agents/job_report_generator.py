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
MIN_SCORE = 20
LIMIT = 30

ACTIONABLE_BUCKETS = [
    "Strong Match",
    "Good Match",
    "Weak Match",
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


def fetch_bucket_summary(conn):
    query = """
        SELECT
            COALESCE(fit_bucket, 'Unclassified') AS fit_bucket,
            COUNT(*) AS job_count
        FROM job_scores
        WHERE scoring_version = %s
        GROUP BY COALESCE(fit_bucket, 'Unclassified')
        ORDER BY job_count DESC;
    """

    with conn.cursor() as cur:
        cur.execute(query, (SCORING_VERSION,))
        return cur.fetchall()


def fetch_top_jobs(conn):
    query = """
        SELECT
            js.overall_score,
            js.fit_bucket,
            js.role_score,
            js.skill_score,
            js.experience_score,
            js.location_score,
            js.penalty_score,
            j.source_name,
            j.title,
            j.company_name,
            j.location,
            j.job_type,
            j.category,
            j.job_url,
            js.matched_keywords,
            js.red_flags,
            js.recommendation,
            js.score_summary,
            js.scored_at
        FROM job_scores js
        JOIN jobs_normalized j
            ON js.normalized_job_id = j.id
        WHERE
            js.scoring_version = %s
            AND COALESCE(j.is_duplicate, FALSE) = FALSE
            AND js.overall_score >= %s
            AND js.fit_bucket = ANY(%s)
        ORDER BY
            js.overall_score DESC,
            js.skill_score DESC,
            js.role_score DESC,
            js.scored_at DESC
        LIMIT %s;
    """

    with conn.cursor() as cur:
        cur.execute(
            query,
            (
                SCORING_VERSION,
                MIN_SCORE,
                ACTIONABLE_BUCKETS,
                LIMIT,
            ),
        )
        return cur.fetchall()


def write_markdown_report(rows, bucket_summary):
    generated_at = datetime.now().isoformat(timespec="seconds")

    lines = []
    lines.append("# AI Job Agent - Top Job Matches Report")
    lines.append("")
    lines.append(f"Generated at: {generated_at}")
    lines.append(f"Scoring version: `{SCORING_VERSION}`")
    lines.append(f"Minimum score: `{MIN_SCORE}`")
    lines.append(f"Jobs included: `{len(rows)}`")
    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## Fit Bucket Summary")
    lines.append("")

    if bucket_summary:
        lines.append("| Fit Bucket | Job Count |")
        lines.append("|---|---:|")

        for bucket, count in bucket_summary:
            lines.append(f"| {bucket} | {count} |")
    else:
        lines.append("No scoring summary available.")

    lines.append("")
    lines.append("---")
    lines.append("")

    lines.append("## Top Job Matches")
    lines.append("")

    if not rows:
        lines.append("No actionable jobs matched the current score threshold.")
        lines.append("")
        lines.append("Recommended next action: run the pipeline again after adding better job sources.")
    else:
        for index, row in enumerate(rows, start=1):
            (
                overall_score,
                fit_bucket,
                role_score,
                skill_score,
                experience_score,
                location_score,
                penalty_score,
                source_name,
                title,
                company_name,
                location,
                job_type,
                category,
                job_url,
                matched_keywords,
                red_flags,
                recommendation,
                score_summary,
                scored_at,
            ) = row

            lines.append(f"## {index}. {title}")
            lines.append("")
            lines.append(f"**Company:** {company_name}")
            lines.append(f"**Source:** {source_name}")
            lines.append(f"**Location:** {location}")
            lines.append(f"**Job Type:** {job_type}")
            lines.append(f"**Category:** {category}")
            lines.append(f"**Fit Bucket:** {fit_bucket}")
            lines.append(f"**Overall Score:** {overall_score}/100")
            lines.append("")

            lines.append("### Score Breakdown")
            lines.append("")
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

            lines.append("### Recommendation")
            lines.append("")
            lines.append(recommendation or "")
            lines.append("")

            lines.append("### Score Summary")
            lines.append("")
            lines.append(score_summary or "")
            lines.append("")
            lines.append(f"**Scored At:** {scored_at}")
            lines.append(f"**Job URL:** {job_url}")
            lines.append("")
            lines.append("---")
            lines.append("")

    with open(MARKDOWN_REPORT, "w", encoding="utf-8") as file:
        file.write("\n".join(lines))


def write_csv_report(rows):
    fieldnames = [
        "overall_score",
        "fit_bucket",
        "role_score",
        "skill_score",
        "experience_score",
        "location_score",
        "penalty_score",
        "source_name",
        "title",
        "company_name",
        "location",
        "job_type",
        "category",
        "job_url",
        "matched_keywords",
        "red_flags",
        "recommendation",
        "score_summary",
        "scored_at",
    ]

    with open(CSV_REPORT, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(fieldnames)

        for row in rows:
            row = list(row)
            row[14] = format_list(row[14])
            row[15] = format_list(row[15])
            writer.writerow(row)


def main():
    print("Starting top job report generation...")
    print(f"Scoring version: {SCORING_VERSION}")

    REPORTS_DIR.mkdir(exist_ok=True)

    conn = get_db_connection()

    try:
        bucket_summary = fetch_bucket_summary(conn)
        rows = fetch_top_jobs(conn)

        print(f"Fit bucket groups found: {len(bucket_summary)}")
        print(f"Top actionable jobs fetched: {len(rows)}")

        write_markdown_report(rows, bucket_summary)
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