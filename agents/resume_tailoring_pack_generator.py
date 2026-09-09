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

TAILORING_MD = EXPORTS_DIR / "resume_tailoring_pack.md"
TAILORING_CSV = EXPORTS_DIR / "resume_tailoring_pack.csv"

TAILORING_LIMIT = 40


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


def to_list(value):
    if value is None:
        return []

    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]

    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]

    return [str(value).strip()]


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
            j.description,
            js.role_score,
            js.skill_score,
            js.experience_score,
            js.location_score,
            js.penalty_score,
            js.matched_keywords,
            js.missing_keywords,
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
        cur.execute(query, (SCORING_VERSION, TAILORING_LIMIT))
        return cur.fetchall()


def build_profile_summary(profile):
    return {
        "candidate_name": profile.get("candidate_name", "Rachit Srivastava"),
        "current_role": profile.get("current_role", "Cloud Support Engineer"),
        "experience_years": profile.get("experience_years", 2.6),
        "strong_keywords": to_list(profile.get("strong_keywords", [])),
        "learning_keywords": to_list(profile.get("learning_keywords", [])),
    }


def infer_role_family(title, matched_keywords):
    combined = f"{title} {format_list(matched_keywords)}".lower()

    if "sre" in combined or "site reliability" in combined:
        return "SRE / Production Support"

    if "devops" in combined or "ci/cd" in combined or "terraform" in combined:
        return "DevOps / Cloud Operations"

    if "azure" in combined:
        return "Azure Cloud Engineering"

    if "aws" in combined:
        return "AWS Cloud Engineering"

    if "iam" in combined or "identity" in combined or "active directory" in combined or "entra" in combined:
        return "IAM / Identity Support"

    if "support" in combined:
        return "Technical / Cloud Support"

    if "cloud" in combined or "infrastructure" in combined or "platform" in combined:
        return "Cloud / Infrastructure Engineering"

    return "Cloud Support / Infrastructure Operations"


def build_resume_headline(role_family, title):
    if role_family == "DevOps / Cloud Operations":
        return "Cloud Support Engineer transitioning into DevOps | Incident Management | CI/CD | Automation | Azure/AWS"

    if role_family == "SRE / Production Support":
        return "Cloud Support Engineer | Production Support | RCA | Incident Response | Linux/Networking | SRE Transition"

    if role_family == "Azure Cloud Engineering":
        return "Azure Cloud Support Engineer | Infrastructure Troubleshooting | IAM/AD Exposure | Automation Learning"

    if role_family == "AWS Cloud Engineering":
        return "AWS / Cloud Support Engineer | Infrastructure Troubleshooting | Incident Ownership | DevOps Learning"

    if role_family == "IAM / Identity Support":
        return "IAM / Cloud Support Engineer | Active Directory | Entra ID | Access Troubleshooting | Audit Support"

    if role_family == "Technical / Cloud Support":
        return "Technical Support Engineer | Cloud Support | RCA | Escalation Management | SLA Ownership"

    return "Cloud & Infrastructure Support Engineer | Troubleshooting | RCA | Automation | DevOps Learning"


def build_summary_angle(profile_summary, role_family, job):
    title = job["title"]
    company = job["company_name"]

    base = (
        f"Rewrite the resume summary toward the {title} role at {company}. "
        f"Position the candidate as a {profile_summary['current_role']} with around "
        f"{profile_summary['experience_years']} years of enterprise support experience."
    )

    if role_family == "DevOps / Cloud Operations":
        return (
            base
            + " Emphasize incident ownership, troubleshooting, RCA, escalation management, cloud support, and current hands-on DevOps learning around CI/CD, Docker, Kubernetes, Terraform, Python, SQL, and automation."
        )

    if role_family == "SRE / Production Support":
        return (
            base
            + " Emphasize production support, incident response, monitoring mindset, RCA, Linux/networking troubleshooting, SLA handling, and reliability-focused operations."
        )

    if role_family == "Azure Cloud Engineering":
        return (
            base
            + " Emphasize Azure support, cloud infrastructure troubleshooting, Microsoft ecosystem exposure, identity basics, Active Directory/Entra ID familiarity, and automation learning."
        )

    if role_family == "AWS Cloud Engineering":
        return (
            base
            + " Emphasize AWS fundamentals, cloud operations, infrastructure troubleshooting, incident handling, and automation-focused learning."
        )

    if role_family == "IAM / Identity Support":
        return (
            base
            + " Emphasize Active Directory, Entra ID/IAM familiarity, access troubleshooting, compliance mindset, audit support, scripting basics, and stakeholder communication."
        )

    if role_family == "Technical / Cloud Support":
        return (
            base
            + " Emphasize technical troubleshooting, customer/stakeholder communication, ticket ownership, RCA, escalation handling, documentation, SLA adherence, and cloud support exposure."
        )

    return (
        base
        + " Emphasize cloud support, infrastructure troubleshooting, incident ownership, RCA, documentation, and practical automation learning."
    )


def build_skills_to_emphasize(role_family, matched_keywords, profile_summary):
    matched = to_list(matched_keywords)

    core_skills = [
        "Technical troubleshooting",
        "Incident ownership",
        "Root Cause Analysis",
        "Escalation management",
        "SLA handling",
        "Documentation",
        "Stakeholder communication",
    ]

    role_skills = []

    if role_family == "DevOps / Cloud Operations":
        role_skills = [
            "CI/CD fundamentals",
            "Git/GitHub",
            "Docker basics",
            "Kubernetes basics",
            "Terraform basics",
            "Python automation",
            "SQL/PostgreSQL",
            "Cloud operations",
        ]

    elif role_family == "SRE / Production Support":
        role_skills = [
            "Production support",
            "Monitoring mindset",
            "Linux troubleshooting",
            "Networking fundamentals",
            "Incident response",
            "RCA documentation",
            "Reliability thinking",
        ]

    elif role_family == "Azure Cloud Engineering":
        role_skills = [
            "Azure fundamentals",
            "Azure infrastructure support",
            "Active Directory",
            "Entra ID basics",
            "Windows Server",
            "DNS/networking troubleshooting",
            "PowerShell basics",
        ]

    elif role_family == "AWS Cloud Engineering":
        role_skills = [
            "AWS fundamentals",
            "Cloud infrastructure support",
            "Linux basics",
            "Networking/DNS",
            "Incident management",
            "Automation learning",
        ]

    elif role_family == "IAM / Identity Support":
        role_skills = [
            "Active Directory",
            "Entra ID",
            "IAM basics",
            "Access troubleshooting",
            "Compliance support",
            "Audit evidence support",
            "PowerShell basics",
        ]

    elif role_family == "Technical / Cloud Support":
        role_skills = [
            "L1/L2/L3 support",
            "Ticket ownership",
            "Customer communication",
            "Technical documentation",
            "Cloud support",
            "RCA",
            "Escalation management",
        ]

    all_skills = core_skills + role_skills

    for keyword in matched:
        pretty = keyword.strip()
        if pretty and pretty.lower() not in [skill.lower() for skill in all_skills]:
            all_skills.append(pretty)

    return all_skills[:18]


def build_projects_to_mention(role_family):
    projects = [
        "AI Job Agent: Python + PostgreSQL project that ingests jobs, normalizes them, deduplicates, scores candidate fit, generates decisions, and exports application reports.",
    ]

    if role_family in ["DevOps / Cloud Operations", "SRE / Production Support"]:
        projects.append(
            "Highlight the project as an automation pipeline with modular agents, versioned scoring, CI-friendly structure, and repeatable execution through a pipeline runner."
        )

    if role_family in ["Azure Cloud Engineering", "AWS Cloud Engineering", "Cloud / Infrastructure Engineering"]:
        projects.append(
            "Mention cloud migration / infrastructure troubleshooting exposure from work experience, especially routing, connectivity checks, incident handling, and documentation."
        )

    if role_family == "IAM / Identity Support":
        projects.append(
            "Mention IAM/AD/Entra ID learning and any support exposure around user access, authentication, permissions, or audit/compliance evidence."
        )

    return projects


def build_experience_bullet_angles(role_family):
    common_bullets = [
        "Rewrite support work as ownership of technical incidents from investigation to resolution.",
        "Show RCA and documentation as repeatable engineering habits, not only support tasks.",
        "Mention collaboration with internal teams, escalation handling, SLA awareness, and stakeholder updates.",
    ]

    if role_family == "DevOps / Cloud Operations":
        return common_bullets + [
            "Add bullets showing automation mindset, script-assisted checks, deployment/support coordination, and learning around CI/CD tools.",
            "Mention Python/SQL as hands-on learning only; do not present them as deep production experience unless true.",
        ]

    if role_family == "SRE / Production Support":
        return common_bullets + [
            "Add bullets around production issue triage, monitoring/alert response, logs, service impact, and reliability improvement.",
            "Use words like uptime, RCA, incident response, post-incident documentation, and recurring issue prevention where accurate.",
        ]

    if role_family == "Azure Cloud Engineering":
        return common_bullets + [
            "Add Azure/AWS certification and cloud troubleshooting context near the top.",
            "Mention Windows Server, DNS, networking, Active Directory, and Entra ID exposure where accurate.",
        ]

    if role_family == "AWS Cloud Engineering":
        return common_bullets + [
            "Add AWS certification and cloud fundamentals prominently.",
            "Mention infrastructure troubleshooting, networking, Linux, and automation learning where accurate.",
        ]

    if role_family == "IAM / Identity Support":
        return common_bullets + [
            "Add identity/access troubleshooting, Active Directory, Entra ID, audit support, and compliance-follow-up wording where accurate.",
            "Mention PowerShell/Python/Bash only as familiarity or learning unless production usage exists.",
        ]

    if role_family == "Technical / Cloud Support":
        return common_bullets + [
            "Keep support engineering as the core strength: ticket ownership, troubleshooting, RCA, customer communication, and escalation.",
            "Add cloud/platform exposure as the growth direction rather than over-positioning as pure DevOps.",
        ]

    return common_bullets


def build_keywords_to_handle_carefully(missing_keywords, red_flags, profile_summary):
    missing = to_list(missing_keywords)
    red_flags = to_list(red_flags)
    learning = [item.lower() for item in profile_summary.get("learning_keywords", [])]

    careful = []

    for keyword in missing[:10]:
        keyword_lower = keyword.lower()

        if keyword_lower in learning:
            careful.append(
                f"{keyword}: mention as hands-on learning/project exposure only, unless you have real production experience."
            )
        else:
            careful.append(
                f"{keyword}: do not force into resume unless it genuinely matches your experience."
            )

    for flag in red_flags:
        careful.append(
            f"Red flag '{flag}': check whether the role is too senior or outside target before applying."
        )

    if not careful:
        careful.append(
            "No major missing-keyword warning from the current scoring data. Still avoid exaggerating production experience."
        )

    return careful[:12]


def build_tailoring_record(profile_summary, row):
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
        description,
        role_score,
        skill_score,
        experience_score,
        location_score,
        penalty_score,
        matched_keywords,
        missing_keywords,
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
        "description": description,
        "role_score": role_score,
        "skill_score": skill_score,
        "experience_score": experience_score,
        "location_score": location_score,
        "penalty_score": penalty_score,
        "matched_keywords": matched_keywords,
        "missing_keywords": missing_keywords,
        "red_flags": red_flags,
        "decision_reason": decision_reason,
        "recommendation": recommendation,
    }

    role_family = infer_role_family(title, matched_keywords)

    return {
        **job,
        "role_family": role_family,
        "resume_headline": build_resume_headline(role_family, title),
        "summary_angle": build_summary_angle(profile_summary, role_family, job),
        "skills_to_emphasize": build_skills_to_emphasize(
            role_family,
            matched_keywords,
            profile_summary,
        ),
        "projects_to_mention": build_projects_to_mention(role_family),
        "experience_bullet_angles": build_experience_bullet_angles(role_family),
        "keywords_to_handle_carefully": build_keywords_to_handle_carefully(
            missing_keywords,
            red_flags,
            profile_summary,
        ),
    }


def write_markdown(records):
    generated_at = datetime.now().isoformat(timespec="seconds")

    lines = []
    lines.append("# AI Job Agent - Resume Tailoring Input Pack")
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
        lines.append(f"**Role Family:** {record['role_family']}")
        lines.append(f"**Source:** {record['source_name']}")
        lines.append(f"**Location:** {record['location']}")
        lines.append(f"**Category:** {record['category']}")
        lines.append(f"**Job URL:** {record['job_url']}")
        lines.append("")

        lines.append("### Resume Headline Suggestion")
        lines.append("")
        lines.append(record["resume_headline"])
        lines.append("")

        lines.append("### Summary Rewrite Angle")
        lines.append("")
        lines.append(record["summary_angle"])
        lines.append("")

        lines.append("### Skills to Emphasize")
        lines.append("")
        for skill in record["skills_to_emphasize"]:
            lines.append(f"- {skill}")
        lines.append("")

        lines.append("### Projects to Mention")
        lines.append("")
        for project in record["projects_to_mention"]:
            lines.append(f"- {project}")
        lines.append("")

        lines.append("### Experience Bullet Angles")
        lines.append("")
        for bullet in record["experience_bullet_angles"]:
            lines.append(f"- {bullet}")
        lines.append("")

        lines.append("### Keywords to Handle Carefully")
        lines.append("")
        for warning in record["keywords_to_handle_carefully"]:
            lines.append(f"- {warning}")
        lines.append("")

        lines.append("### Scoring Context")
        lines.append("")
        lines.append(f"**Matched Keywords:** {format_list(record['matched_keywords'])}")
        lines.append(f"**Missing Keywords:** {format_list(record['missing_keywords'])}")
        lines.append(f"**Red Flags:** {format_list(record['red_flags'])}")
        lines.append("")
        lines.append(f"- Role Score: {record['role_score']}/100")
        lines.append(f"- Skill Score: {record['skill_score']}/100")
        lines.append(f"- Experience Score: {record['experience_score']}/100")
        lines.append(f"- Location Score: {record['location_score']}/100")
        lines.append(f"- Penalty Score: {record['penalty_score']}")
        lines.append("")
        lines.append(f"**Decision Reason:** {record['decision_reason']}")
        lines.append(f"**Recommendation:** {record['recommendation']}")
        lines.append("")
        lines.append("---")
        lines.append("")

    with open(TAILORING_MD, "w", encoding="utf-8") as file:
        file.write("\n".join(lines))


def write_csv(records):
    headers = [
        "rank",
        "job_id",
        "decision_status",
        "priority_score",
        "fit_bucket",
        "role_family",
        "source_name",
        "title",
        "company_name",
        "location",
        "category",
        "job_url",
        "resume_headline",
        "summary_angle",
        "skills_to_emphasize",
        "projects_to_mention",
        "experience_bullet_angles",
        "keywords_to_handle_carefully",
        "matched_keywords",
        "missing_keywords",
        "red_flags",
    ]

    with open(TAILORING_CSV, "w", newline="", encoding="utf-8") as file:
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
                    record["role_family"],
                    record["source_name"],
                    record["title"],
                    record["company_name"],
                    record["location"],
                    record["category"],
                    record["job_url"],
                    record["resume_headline"],
                    record["summary_angle"],
                    " | ".join(record["skills_to_emphasize"]),
                    " | ".join(record["projects_to_mention"]),
                    " | ".join(record["experience_bullet_angles"]),
                    " | ".join(record["keywords_to_handle_carefully"]),
                    format_list(record["matched_keywords"]),
                    format_list(record["missing_keywords"]),
                    format_list(record["red_flags"]),
                ]
            )


def main():
    print("Starting resume tailoring pack generation...")

    EXPORTS_DIR.mkdir(exist_ok=True)

    profile = load_candidate_profile()
    profile_summary = build_profile_summary(profile)

    conn = get_db_connection()

    try:
        rows = fetch_actionable_jobs(conn)
        records = [
            build_tailoring_record(profile_summary, row)
            for row in rows
        ]

        write_markdown(records)
        write_csv(records)

        print("Resume tailoring pack generation completed.")
        print(f"Tailoring briefs generated: {len(records)}")
        print(f"Markdown output: {TAILORING_MD}")
        print(f"CSV output: {TAILORING_CSV}")

    except Exception as error:
        print("Resume tailoring pack generation failed.")
        print(error)

    finally:
        conn.close()


if __name__ == "__main__":
    main()