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
SCORING_VERSION = "rule_v0.1"


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


def calculate_role_score(profile, title_text, combined_text):
    role_keywords = profile.get("role_keywords", [])

    title_matches = []
    description_matches = []

    for keyword in role_keywords:
        if keyword_found(keyword, title_text):
            title_matches.append(keyword)
        elif keyword_found(keyword, combined_text):
            description_matches.append(keyword)

    score = 0

    if title_matches:
        score += 70

    score += min(len(description_matches) * 10, 30)

    return min(score, 100), title_matches + description_matches


def calculate_skill_score(profile, combined_text):
    strong_keywords = profile.get("strong_keywords", [])
    learning_keywords = profile.get("learning_keywords", [])

    matched = []
    missing = []

    score = 0

    for keyword in strong_keywords:
        if keyword_found(keyword, combined_text):
            matched.append(keyword)
            score += 8
        else:
            missing.append(keyword)

    for keyword in learning_keywords:
        if keyword_found(keyword, combined_text):
            matched.append(keyword)
            score += 4
        else:
            missing.append(keyword)

    return min(score, 100), matched, missing


def calculate_experience_score(title_text, combined_text):
    red_flags = []
    score = 80

    senior_terms = {
        "senior": 10,
        "lead": 20,
        "principal": 35,
        "staff engineer": 30,
        "architect": 25,
        "manager": 30,
        "director": 45,
        "head of": 50,
        "10+ years": 40,
        "12+ years": 45,
        "15+ years": 50,
    }

    for term, penalty in senior_terms.items():
        if keyword_found(term, title_text) or keyword_found(term, combined_text):
            red_flags.append(term)
            score -= penalty

    return max(score, 10), red_flags


def calculate_location_score(profile, location_text, combined_text):
    preferred_locations = profile.get("preferred_locations", [])
    preferred_work_modes = profile.get("preferred_work_modes", [])

    location_text = normalize_text(location_text)
    combined_text = normalize_text(combined_text)

    for mode in preferred_work_modes:
        if keyword_found(mode, location_text) or keyword_found(mode, combined_text):
            return 100

    for location in preferred_locations:
        if keyword_found(location, location_text) or keyword_found(location, combined_text):
            return 90

    remote_indicators = [
        "worldwide",
        "anywhere",
        "global",
        "americas",
        "europe",
        "emea"
    ]

    for indicator in remote_indicators:
        if keyword_found(indicator, location_text):
            return 75

    if not location_text:
        return 40

    return 50


def calculate_penalty_score(profile, combined_text):
    negative_keywords = profile.get("negative_keywords", [])

    red_flags = []
    penalty = 0

    for keyword in negative_keywords:
        if keyword_found(keyword, combined_text):
            red_flags.append(keyword)
            penalty += 10

    return min(penalty, 50), red_flags


def build_score_summary(overall, role_score, skill_score, experience_score, location_score, penalty_score):
    return (
        f"Overall score {overall}/100. "
        f"Role relevance: {role_score}/100, "
        f"skill match: {skill_score}/100, "
        f"experience fit: {experience_score}/100, "
        f"location fit: {location_score}/100, "
        f"penalty: {penalty_score}."
    )


def score_job(profile, job):
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

    role_score, role_matches = calculate_role_score(profile, title_text, combined_text)
    skill_score, matched_skills, missing_skills = calculate_skill_score(profile, combined_text)
    experience_score, experience_flags = calculate_experience_score(title_text, combined_text)
    location_score = calculate_location_score(profile, location, combined_text)
    penalty_score, negative_flags = calculate_penalty_score(profile, combined_text)

    overall_score = round(
        (role_score * 0.30)
        + (skill_score * 0.35)
        + (experience_score * 0.20)
        + (location_score * 0.15)
        - penalty_score
    )

    overall_score = max(0, min(overall_score, 100))

    all_red_flags = sorted(set(experience_flags + negative_flags))

    return {
        "normalized_job_id": job_id,
        "overall_score": overall_score,
        "role_score": role_score,
        "skill_score": skill_score,
        "experience_score": experience_score,
        "location_score": location_score,
        "penalty_score": penalty_score,
        "matched_keywords": sorted(set(role_matches + matched_skills)),
        "missing_keywords": missing_skills,
        "red_flags": all_red_flags,
        "score_summary": build_score_summary(
            overall_score,
            role_score,
            skill_score,
            experience_score,
            location_score,
            penalty_score,
        ),
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
            scored_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
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
            ),
        )


def main():
    print("Starting job match scoring...")

    profile = load_candidate_profile()
    conn = get_db_connection()

    try:
        jobs = fetch_jobs_to_score(conn)
        print(f"Jobs available for scoring: {len(jobs)}")

        scored_count = 0

        for job in jobs:
            score = score_job(profile, job)
            save_job_score(conn, score)
            scored_count += 1

            print(
                f"Scored job ID {score['normalized_job_id']} "
                f"= {score['overall_score']}/100"
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