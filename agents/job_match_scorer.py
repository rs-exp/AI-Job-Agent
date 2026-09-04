import json
import os
import re
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
PROFILE_FILE = BASE_DIR / "data" / "candidate_profile.json"
SCORING_VERSION = "rule_v0.2"


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
        raise FileNotFoundError(
            "candidate_profile.json not found. "
            "Create it from data/candidate_profile.example.json"
        )

    with open(PROFILE_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def normalize_text(value):
    if not value:
        return ""

    value = str(value).lower()
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"[^a-z0-9+#.\s/-]", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def keyword_found(keyword, text):
    keyword = normalize_text(keyword)

    if not keyword:
        return False

    return keyword in text


def fetch_jobs_to_score(conn):
    query = """
        SELECT
            id,
            title,
            company_name,
            location,
            job_type,
            category,
            tags,
            description,
            job_url
        FROM jobs_normalized
        WHERE COALESCE(is_duplicate, FALSE) = FALSE
        ORDER BY id ASC;
    """

    with conn.cursor() as cur:
        cur.execute(query)
        return cur.fetchall()


TARGET_TITLE_KEYWORDS = [
    "devops",
    "cloud engineer",
    "cloud support",
    "site reliability",
    "sre",
    "platform engineer",
    "azure",
    "aws",
    "infrastructure engineer",
    "systems engineer",
    "technical support engineer",
    "linux engineer",
    "cloud operations",
]

GOOD_BODY_KEYWORDS = [
    "azure",
    "aws",
    "cloud",
    "devops",
    "sre",
    "platform",
    "kubernetes",
    "docker",
    "terraform",
    "jenkins",
    "ci/cd",
    "github actions",
    "linux",
    "windows server",
    "active directory",
    "entra id",
    "iam",
    "incident",
    "troubleshooting",
    "monitoring",
    "automation",
    "python",
    "sql",
    "postgresql",
    "powershell",
    "networking",
    "dns",
]

SUPPORT_STRENGTH_KEYWORDS = [
    "technical support",
    "customer support",
    "incident management",
    "troubleshooting",
    "root cause",
    "rca",
    "escalation",
    "sla",
    "operations",
    "support engineer",
]

LEARNING_KEYWORDS = [
    "python",
    "sql",
    "postgresql",
    "docker",
    "kubernetes",
    "terraform",
    "jenkins",
    "github actions",
    "automation",
    "ci/cd",
    "devops",
]

HARD_NEGATIVE_TITLE_KEYWORDS = [
    "copywriter",
    "writer",
    "sales",
    "marketing",
    "business development",
    "partnership",
    "customer care",
    "customer service",
    "content reviewer",
    "head of marketing",
    "brand",
    "e-commerce",
    "working student",
    "intern",
    "praktikant",
    "student",
]

SENIORITY_RISK_KEYWORDS = [
    "head of",
    "director",
    "vp",
    "principal",
    "staff engineer",
    "architect",
    "manager",
    "lead",
    "10+ years",
    "12+ years",
    "15+ years",
]


def calculate_role_score(title_text, combined_text):
    title_matches = []
    body_matches = []

    score = 0

    for keyword in TARGET_TITLE_KEYWORDS:
        if keyword_found(keyword, title_text):
            title_matches.append(keyword)
        elif keyword_found(keyword, combined_text):
            body_matches.append(keyword)

    if title_matches:
        score += 65

    score += min(len(body_matches) * 6, 30)

    if not title_matches and body_matches:
        score += 10

    return min(score, 100), sorted(set(title_matches + body_matches))


def calculate_skill_score(combined_text):
    matched = []
    missing = []
    score = 0

    for keyword in GOOD_BODY_KEYWORDS:
        if keyword_found(keyword, combined_text):
            matched.append(keyword)
            score += 5
        else:
            missing.append(keyword)

    for keyword in SUPPORT_STRENGTH_KEYWORDS:
        if keyword_found(keyword, combined_text):
            matched.append(keyword)
            score += 4

    for keyword in LEARNING_KEYWORDS:
        if keyword_found(keyword, combined_text):
            matched.append(keyword)
            score += 3

    return min(score, 100), sorted(set(matched)), missing


def calculate_experience_score(title_text, combined_text):
    score = 80
    flags = []

    if keyword_found("junior", title_text) or keyword_found("associate", title_text):
        score += 10

    if keyword_found("mid", title_text):
        score += 5

    for keyword in SENIORITY_RISK_KEYWORDS:
        if keyword_found(keyword, title_text) or keyword_found(keyword, combined_text):
            flags.append(keyword)

            if keyword in ["head of", "director", "vp"]:
                score -= 45
            elif keyword in ["principal", "staff engineer", "architect"]:
                score -= 30
            elif keyword in ["manager", "lead"]:
                score -= 20
            else:
                score -= 25

    return max(5, min(score, 100)), sorted(set(flags))


def calculate_location_score(location_text, combined_text):
    location_text = normalize_text(location_text)
    combined_text = normalize_text(combined_text)

    excellent_locations = [
        "remote",
        "india",
        "pune",
        "mumbai",
        "bengaluru",
        "bangalore",
        "hyderabad",
        "noida",
        "gurugram",
        "gurgaon",
    ]

    good_remote_regions = [
        "worldwide",
        "anywhere",
        "global",
        "emea",
        "asia",
        "apac",
        "americas",
        "europe",
    ]

    for keyword in excellent_locations:
        if keyword_found(keyword, location_text) or keyword_found(keyword, combined_text):
            return 100

    for keyword in good_remote_regions:
        if keyword_found(keyword, location_text):
            return 75

    if not location_text:
        return 40

    return 45


def calculate_penalty_score(title_text, combined_text):
    penalty = 0
    red_flags = []

    for keyword in HARD_NEGATIVE_TITLE_KEYWORDS:
        if keyword_found(keyword, title_text):
            red_flags.append(keyword)
            penalty += 35
        elif keyword_found(keyword, combined_text):
            red_flags.append(keyword)
            penalty += 15

    non_target_domains = [
        "marketing",
        "sales",
        "copywriting",
        "content",
        "brand",
        "customer care",
        "e-commerce",
        "partnership",
    ]

    for keyword in non_target_domains:
        if keyword_found(keyword, title_text):
            red_flags.append(keyword)
            penalty += 20

    return min(penalty, 80), sorted(set(red_flags))


def calculate_fit_bucket(overall_score, red_flags):
    severe_flags = {
        "copywriter",
        "writer",
        "sales",
        "marketing",
        "business development",
        "working student",
        "intern",
        "student",
    }

    if any(flag in severe_flags for flag in red_flags):
        if overall_score < 55:
            return "Reject"

    if overall_score >= 75:
        return "Strong Match"

    if overall_score >= 55:
        return "Good Match"

    if overall_score >= 35:
        return "Weak Match"

    return "Reject"


def build_recommendation(fit_bucket, overall_score, red_flags, matched_keywords):
    if fit_bucket == "Strong Match":
        return "Apply or review immediately. This role aligns well with the Cloud/DevOps transition path."

    if fit_bucket == "Good Match":
        return "Review manually. The role has useful alignment but may need resume tailoring."

    if fit_bucket == "Weak Match":
        return "Low priority. Keep only if the role has hidden relevance after manual review."

    if red_flags:
        return f"Skip for now. Red flags detected: {', '.join(red_flags)}."

    return "Skip for now. Score is too low for the current target profile."


def build_score_summary(
    overall,
    role_score,
    skill_score,
    experience_score,
    location_score,
    penalty_score,
    fit_bucket,
):
    return (
        f"Overall score {overall}/100. "
        f"Fit bucket: {fit_bucket}. "
        f"Role relevance: {role_score}/100, "
        f"skill match: {skill_score}/100, "
        f"experience fit: {experience_score}/100, "
        f"location fit: {location_score}/100, "
        f"penalty: {penalty_score}."
    )


def score_job(job):
    (
        job_id,
        title,
        company_name,
        location,
        job_type,
        category,
        tags,
        description,
        job_url,
    ) = job

    tags_text = " ".join(tags or []) if isinstance(tags, list) else str(tags or "")

    title_text = normalize_text(title)
    combined_text = normalize_text(
        " ".join(
            [
                title or "",
                company_name or "",
                location or "",
                job_type or "",
                category or "",
                tags_text,
                description or "",
            ]
        )
    )

    role_score, role_matches = calculate_role_score(title_text, combined_text)
    skill_score, matched_skills, missing_skills = calculate_skill_score(combined_text)
    experience_score, experience_flags = calculate_experience_score(title_text, combined_text)
    location_score = calculate_location_score(location, combined_text)
    penalty_score, negative_flags = calculate_penalty_score(title_text, combined_text)

    red_flags = sorted(set(experience_flags + negative_flags))
    matched_keywords = sorted(set(role_matches + matched_skills))

    overall_score = round(
        (role_score * 0.35)
        + (skill_score * 0.35)
        + (experience_score * 0.15)
        + (location_score * 0.15)
        - penalty_score
    )

    overall_score = max(0, min(overall_score, 100))

    fit_bucket = calculate_fit_bucket(overall_score, red_flags)
    recommendation = build_recommendation(
        fit_bucket,
        overall_score,
        red_flags,
        matched_keywords,
    )

    return {
        "normalized_job_id": job_id,
        "overall_score": overall_score,
        "role_score": role_score,
        "skill_score": skill_score,
        "experience_score": experience_score,
        "location_score": location_score,
        "penalty_score": penalty_score,
        "matched_keywords": matched_keywords,
        "missing_keywords": missing_skills,
        "red_flags": red_flags,
        "score_summary": build_score_summary(
            overall_score,
            role_score,
            skill_score,
            experience_score,
            location_score,
            penalty_score,
            fit_bucket,
        ),
        "fit_bucket": fit_bucket,
        "recommendation": recommendation,
    }


def save_job_score(conn, score):
    query = """
        INSERT INTO job_scores (
            normalized_job_id,
            scoring_version,
            overall_score,
            role_score,
            skill_score,
            experience_score,
            location_score,
            penalty_score,
            matched_keywords,
            missing_keywords,
            red_flags,
            score_summary,
            fit_bucket,
            recommendation,
            scored_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (normalized_job_id, scoring_version)
        DO UPDATE SET
            overall_score = EXCLUDED.overall_score,
            role_score = EXCLUDED.role_score,
            skill_score = EXCLUDED.skill_score,
            experience_score = EXCLUDED.experience_score,
            location_score = EXCLUDED.location_score,
            penalty_score = EXCLUDED.penalty_score,
            matched_keywords = EXCLUDED.matched_keywords,
            missing_keywords = EXCLUDED.missing_keywords,
            red_flags = EXCLUDED.red_flags,
            score_summary = EXCLUDED.score_summary,
            fit_bucket = EXCLUDED.fit_bucket,
            recommendation = EXCLUDED.recommendation,
            scored_at = CURRENT_TIMESTAMP;
    """

    with conn.cursor() as cur:
        cur.execute(
            query,
            (
                score["normalized_job_id"],
                SCORING_VERSION,
                score["overall_score"],
                score["role_score"],
                score["skill_score"],
                score["experience_score"],
                score["location_score"],
                score["penalty_score"],
                Jsonb(score["matched_keywords"]),
                Jsonb(score["missing_keywords"]),
                Jsonb(score["red_flags"]),
                score["score_summary"],
                score["fit_bucket"],
                score["recommendation"],
            ),
        )


def main():
    print("Starting job match scoring...")
    print(f"Scoring version: {SCORING_VERSION}")

    conn = get_db_connection()

    try:
        jobs = fetch_jobs_to_score(conn)
        print(f"Jobs available for scoring: {len(jobs)}")

        scored_count = 0

        for job in jobs:
            score = score_job(job)
            save_job_score(conn, score)
            scored_count += 1

            print(
                f"Scored job ID {score['normalized_job_id']} "
                f"= {score['overall_score']}/100 "
                f"({score['fit_bucket']})"
            )

        conn.commit()

        print("\nJob match scoring completed.")
        print(f"Jobs scored: {scored_count}")

    except Exception as error:
        conn.rollback()
        print("Job match scoring failed.")
        print(error)

    finally:
        conn.close()


if __name__ == "__main__":
    main()