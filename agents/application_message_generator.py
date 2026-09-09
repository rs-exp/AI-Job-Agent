import csv
import json
import os
from datetime import datetime
from pathlib import Path

import psycopg
from dotenv import load_dotenv

load_dotenv()

SCORING_VERSION = "rule_v0.2"

BASE_DIR = Path(__file__).resolve().parent.parent
PROFILE_FILE = BASE_DIR / "data" / "candidate_profile.json"
EXPORTS_DIR = BASE_DIR / "exports"

MESSAGES_MD = EXPORTS_DIR / "application_messages.md"
MESSAGES_CSV = EXPORTS_DIR / "application_messages.csv"

MESSAGE_LIMIT = 40


def get_db_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def load_candidate_profile():
    if not PROFILE_FILE.exists():
        return {
            "candidate_name": "Rachit Srivastava",
            "current_role": "Cloud Support Engineer",
            "experience_years": 2.6,
            "strong_keywords": [
                "technical troubleshooting",
                "incident management",
                "RCA",
                "escalation management",
                "cloud support",
                "Azure",
                "AWS",
                "Linux",
                "Windows Server",
                "Active Directory",
            ],
            "learning_keywords": [
                "Python",
                "SQL",
                "DevOps",
                "CI/CD",
                "Docker",
                "Kubernetes",
                "Terraform",
            ],
        }

    with open(PROFILE_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def format_list(value):
    if value is None:
        return ""

    if isinstance(value, list):
        return ", ".join(str(item) for item in value)

    return str(value)


def fetch_actionable_jobs(conn):
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
            jad.recommendation
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
            js.role_score DESC
        LIMIT %s;
    """

    with conn.cursor() as cur:
        cur.execute(query, (SCORING_VERSION, MESSAGE_LIMIT))
        return cur.fetchall()


def infer_role_angle(title, matched_keywords):
    title_lower = str(title or "").lower()
    keyword_text = format_list(matched_keywords).lower()

    combined = f"{title_lower} {keyword_text}"

    if "devops" in combined or "ci/cd" in combined or "terraform" in combined:
        return (
            "DevOps / Cloud Operations",
            "cloud operations, troubleshooting, incident ownership, and hands-on DevOps learning across CI/CD, automation, Docker, Kubernetes, and Terraform",
        )

    if "sre" in combined or "site reliability" in combined:
        return (
            "SRE / Production Support",
            "incident ownership, RCA, monitoring mindset, production troubleshooting, Linux/networking fundamentals, and reliability-focused operations",
        )

    if "azure" in combined:
        return (
            "Azure Cloud",
            "Azure support, identity, infrastructure troubleshooting, incident handling, and cloud operations",
        )

    if "aws" in combined:
        return (
            "AWS Cloud",
            "AWS fundamentals, cloud support, infrastructure troubleshooting, incident handling, and automation learning",
        )

    if "iam" in combined or "identity" in combined or "active directory" in combined:
        return (
            "IAM / Identity Support",
            "Active Directory, Entra ID/IAM fundamentals, access troubleshooting, compliance awareness, and support operations",
        )

    if "support" in combined:
        return (
            "Technical Support / Cloud Support",
            "technical troubleshooting, incident management, RCA, escalation handling, documentation, and stakeholder communication",
        )

    return (
        "Cloud / Infrastructure Support",
        "cloud support, infrastructure troubleshooting, incident ownership, RCA, escalation management, and automation learning",
    )


def build_profile_summary(profile):
    name = profile.get("candidate_name", "Rachit Srivastava")
    current_role = profile.get("current_role", "Cloud Support Engineer")
    experience_years = profile.get("experience_years", 2.6)

    strong_keywords = profile.get("strong_keywords", [])
    learning_keywords = profile.get("learning_keywords", [])

    core_strengths = [
        "technical troubleshooting",
        "incident ownership",
        "RCA",
        "escalation management",
        "documentation",
        "stakeholder communication",
    ]

    for keyword in strong_keywords:
        keyword_text = str(keyword).strip()
        if keyword_text and keyword_text not in core_strengths:
            core_strengths.append(keyword_text)

    learning_focus = []

    for keyword in learning_keywords:
        keyword_text = str(keyword).strip()
        if keyword_text and keyword_text not in learning_focus:
            learning_focus.append(keyword_text)

    return {
        "name": name,
        "current_role": current_role,
        "experience_years": experience_years,
        "core_strengths": core_strengths[:10],
        "learning_focus": learning_focus[:8],
    }


def build_linkedin_message(profile_summary, job):
    title = job["title"]
    company = job["company_name"]
    role_angle, angle_detail = infer_role_angle(
        title,
        job["matched_keywords"],
    )

    return (
        f"Hi, I came across the {title} role at {company}. "
        f"I have around {profile_summary['experience_years']} years of experience in "
        f"enterprise technical/cloud support with strong exposure to troubleshooting, "
        f"incident ownership, RCA, escalation handling, and documentation. "
        f"This role looks aligned with my {role_angle} transition, especially around "
        f"{angle_detail}. I would be glad to connect and share my resume for your review."
    )


def build_email_subject(job):
    return f"Application for {job['title']} role - {job['company_name']}"


def build_email_body(profile_summary, job):
    title = job["title"]
    company = job["company_name"]
    location = job["location"]
    matched_keywords = format_list(job["matched_keywords"])
    role_angle, angle_detail = infer_role_angle(
        title,
        job["matched_keywords"],
    )

    core_strengths = ", ".join(profile_summary["core_strengths"][:6])
    learning_focus = ", ".join(profile_summary["learning_focus"][:6])

    return f"""Hello,

I am writing to express my interest in the {title} role at {company}.

I have around {profile_summary['experience_years']} years of experience in enterprise technical/cloud support, with hands-on strengths in {core_strengths}. My current transition focus is toward {role_angle}, and this opportunity appears aligned with my experience in {angle_detail}.

For this role, the keywords that stood out to me are: {matched_keywords or "cloud, infrastructure, support, and operations"}.

I am also actively building practical skills around {learning_focus or "Python, SQL, DevOps, CI/CD, Docker, Kubernetes, and Terraform"} through project-based learning, including an AI Job Agent project that uses Python, PostgreSQL, job ingestion pipelines, scoring, deduplication, and reporting automation.

Location preference: {location or "open based on role requirements"}.

Please find my resume attached for your review. I would be happy to discuss how my support engineering background and cloud/DevOps learning path can contribute to this role.

Regards,
{profile_summary['name']}"""


def build_easy_apply_note(profile_summary, job):
    title = job["title"]
    company = job["company_name"]
    role_angle, angle_detail = infer_role_angle(
        title,
        job["matched_keywords"],
    )

    return (
        f"I am interested in the {title} role at {company}. "
        f"I bring around {profile_summary['experience_years']} years of enterprise "
        f"technical/cloud support experience across troubleshooting, incident ownership, "
        f"RCA, escalation management, documentation, and stakeholder communication. "
        f"I am currently transitioning toward {role_angle}, with hands-on learning in "
        f"Python, SQL, DevOps, CI/CD, Docker, Kubernetes, and Terraform. "
        f"The role aligns with my background and growth direction around {angle_detail}."
    )


def build_resume_tailoring_angle(job):
    title = str(job["title"] or "").lower()
    matched_keywords = format_list(job["matched_keywords"])

    bullets = []

    if "devops" in title:
        bullets.append("Put DevOps, CI/CD, automation, GitHub, Docker, Kubernetes, and Terraform learning projects near the top.")
        bullets.append("Frame support experience as production troubleshooting, incident ownership, RCA, and deployment/support collaboration.")

    if "cloud" in title or "azure" in title or "aws" in title:
        bullets.append("Highlight cloud support, Azure/AWS certifications, infrastructure troubleshooting, networking, DNS, Linux, and Windows Server.")
        bullets.append("Add one project line about AI Job Agent using Python, PostgreSQL, automation pipeline, and reporting.")

    if "sre" in title or "site reliability" in title:
        bullets.append("Emphasize incident response, monitoring, RCA, production support, Linux/networking troubleshooting, and reliability mindset.")

    if "support" in title:
        bullets.append("Keep technical support, SLA ownership, escalation management, documentation, and stakeholder communication as the core theme.")

    if "iam" in title or "identity" in title:
        bullets.append("Highlight Active Directory, Entra ID/IAM, access troubleshooting, compliance controls, and audit-support exposure.")

    if not bullets:
        bullets.append("Tailor the resume toward cloud support, infrastructure troubleshooting, incident ownership, RCA, and automation learning.")

    bullets.append(f"Matched keywords to reflect carefully: {matched_keywords or 'cloud, support, troubleshooting, automation'}")

    return bullets


def build_message_record(profile_summary, row):
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
        matched_keywords,
        red_flags,
        decision_reason,
        recommendation,
    ) = row

    job = {
        "job_id": job_id,
        "decision_status": decision_status,
        "priority_score": priority_score,
        "fit_bucket": fit_bucket,
        "source_name": source_name,
        "title": title,
        "company_name": company_name,
        "location": location,
        "job_type": job_type,
        "category": category,
        "job_url": job_url,
        "matched_keywords": matched_keywords,
        "red_flags": red_flags,
        "decision_reason": decision_reason,
        "recommendation": recommendation,
    }

    return {
        **job,
        "email_subject": build_email_subject(job),
        "linkedin_message": build_linkedin_message(profile_summary, job),
        "email_body": build_email_body(profile_summary, job),
        "easy_apply_note": build_easy_apply_note(profile_summary, job),
        "resume_tailoring_angle": build_resume_tailoring_angle(job),
    }


def write_markdown(records):
    generated_at = datetime.now().isoformat(timespec="seconds")

    lines = []
    lines.append("# AI Job Agent - Application Messages")
    lines.append("")
    lines.append(f"Generated at: {generated_at}")
    lines.append(f"Scoring version: `{SCORING_VERSION}`")
    lines.append(f"Jobs included: `{len(records)}`")
    lines.append("")
    lines.append("---")
    lines.append("")

    for index, record in enumerate(records, start=1):
        lines.append(f"## {index}. {record['title']} - {record['company_name']}")
        lines.append("")
        lines.append(f"**Job ID:** {record['job_id']}")
        lines.append(f"**Decision:** {record['decision_status']}")
        lines.append(f"**Priority Score:** {record['priority_score']}/100")
        lines.append(f"**Fit Bucket:** {record['fit_bucket']}")
        lines.append(f"**Source:** {record['source_name']}")
        lines.append(f"**Location:** {record['location']}")
        lines.append(f"**Category:** {record['category']}")
        lines.append(f"**Job URL:** {record['job_url']}")
        lines.append("")

        lines.append("### LinkedIn Short Message")
        lines.append("")
        lines.append(record["linkedin_message"])
        lines.append("")

        lines.append("### Email Subject")
        lines.append("")
        lines.append(record["email_subject"])
        lines.append("")

        lines.append("### Email Body")
        lines.append("")
        lines.append(record["email_body"])
        lines.append("")

        lines.append("### Easy Apply Cover Note")
        lines.append("")
        lines.append(record["easy_apply_note"])
        lines.append("")

        lines.append("### Resume Tailoring Angle")
        lines.append("")
        for bullet in record["resume_tailoring_angle"]:
            lines.append(f"- {bullet}")
        lines.append("")

        lines.append("### Decision Context")
        lines.append("")
        lines.append(f"**Decision Reason:** {record['decision_reason']}")
        lines.append(f"**Recommendation:** {record['recommendation']}")
        lines.append(f"**Matched Keywords:** {format_list(record['matched_keywords'])}")
        lines.append(f"**Red Flags:** {format_list(record['red_flags'])}")
        lines.append("")
        lines.append("---")
        lines.append("")

    with open(MESSAGES_MD, "w", encoding="utf-8") as file:
        file.write("\n".join(lines))


def write_csv(records):
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
        "category",
        "job_url",
        "matched_keywords",
        "red_flags",
        "email_subject",
        "linkedin_message",
        "email_body",
        "easy_apply_note",
        "resume_tailoring_angle",
    ]

    with open(MESSAGES_CSV, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(headers)

        for index, record in enumerate(records, start=1):
            writer.writerow(
                [
                    index,
                    record["job_id"],
                    record["decision_status"],
                    record["priority_score"],
                    record["fit_bucket"],
                    record["source_name"],
                    record["title"],
                    record["company_name"],
                    record["location"],
                    record["category"],
                    record["job_url"],
                    format_list(record["matched_keywords"]),
                    format_list(record["red_flags"]),
                    record["email_subject"],
                    record["linkedin_message"],
                    record["email_body"],
                    record["easy_apply_note"],
                    " | ".join(record["resume_tailoring_angle"]),
                ]
            )


def main():
    print("Starting application message generation...")

    EXPORTS_DIR.mkdir(exist_ok=True)

    profile = load_candidate_profile()
    profile_summary = build_profile_summary(profile)

    conn = get_db_connection()

    try:
        rows = fetch_actionable_jobs(conn)
        records = [
            build_message_record(profile_summary, row)
            for row in rows
        ]

        write_markdown(records)
        write_csv(records)

        print("Application message generation completed.")
        print(f"Messages generated: {len(records)}")
        print(f"Markdown output: {MESSAGES_MD}")
        print(f"CSV output: {MESSAGES_CSV}")

    except Exception as error:
        print("Application message generation failed.")
        print(error)

    finally:
        conn.close()


if __name__ == "__main__":
    main()