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

MIN_SCORE = 20
LIMIT = 25


def get_db_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def fetch_top_jobs(conn):
    query = """
        SELECT
            js.overall_score,
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
            js.score_summary
        FROM job_scores js
        JOIN jobs_normalized j
            ON js.normalized_job_id = j.id
        WHERE
            js.scoring_version = 'rule_v0.1'
            AND COALESCE(j.is_duplicate, FALSE) = FALSE
            AND js.overall_score >= %s
        ORDER BY
            js.overall_score DESC,
            js.skill_score DESC,
            js.role_score DESC
        LIMIT %s;
    """

    with conn.cursor() as cur:
        cur.execute(query, (MIN_SCORE, LIMIT))
        return cur.fetchall()


def format_list(value):
    if value is None:
        return ""

    if isinstance(value, list):
        return ", ".join(str(item) for item in value)

    return str(value)


def write_markdown_report(rows):
    generated_at = datetime.now().isoformat(timespec="seconds")

    lines = []
    lines.append("# AI Job Agent - Top Job Matches Report")
    lines.append("")
    lines.append(f"Generated at: {generated_at}")
    lines.append(f"Minimum score: {MIN_SCORE}")
    lines.append(f"Jobs included: {len(rows)}")
    lines.append("")
    lines.append("---")
    lines.append("")

    if not rows:
        lines.append("No jobs matched the current score threshold.")
    else:
        for index, row in enumerate(rows, start=1):
            (
                overall_score,
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
                score_summary,
            ) = row

            lines.append(f"## {index}. {title}")
            lines.append("")
            lines.append(f"**Company:** {company_name}")
            lines.append(f"**Source:** {source_name}")
            lines.append(f"**Location:** {location}")
            lines.append(f"**Job Type:** {job_type}")
            lines.append(f"**Category:** {category}")
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
            lines.append("### Summary")
            lines.append("")
            lines.append(score_summary or "")
            lines.append("")
            lines.append(f"**Job URL:** {job_url}")
            lines.append("")
            lines.append("---")
            lines.append("")

    with open(MARKDOWN_REPORT, "w", encoding="utf-8") as file:
        file.write("\n".join(lines))


def write_csv_report(rows):
    fieldnames = [
        "overall_score",
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
        "score_summary",
    ]

    with open(CSV_REPORT, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(fieldnames)

        for row in rows:
            row = list(row)
            row[13] = format_list(row[13])
            row[14] = format_list(row[14])
            writer.writerow(row)


def main():
    print("Starting top job report generation...")

    REPORTS_DIR.mkdir(exist_ok=True)

    conn = get_db_connection()

    try:
        rows = fetch_top_jobs(conn)

        print(f"Top jobs fetched: {len(rows)}")

        write_markdown_report(rows)
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