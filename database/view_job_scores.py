import os
import psycopg
from dotenv import load_dotenv

load_dotenv()


SCORING_VERSION = "rule_v0.2"


def view_job_scores():
    conn = psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )

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
            j.job_url,
            js.matched_keywords,
            js.red_flags,
            js.recommendation,
            js.score_summary
        FROM job_scores js
        JOIN jobs_normalized j
            ON js.normalized_job_id = j.id
        WHERE js.scoring_version = %s
        ORDER BY js.overall_score DESC, js.skill_score DESC
        LIMIT 15;
    """

    with conn.cursor() as cur:
        cur.execute(query, (SCORING_VERSION,))
        rows = cur.fetchall()

        print(f"Top scored jobs for {SCORING_VERSION}:")
        print("-" * 100)

        for row in rows:
            print(f"Overall Score: {row[0]}/100")
            print(f"Fit Bucket: {row[1]}")
            print(f"Role Score: {row[2]}/100")
            print(f"Skill Score: {row[3]}/100")
            print(f"Experience Score: {row[4]}/100")
            print(f"Location Score: {row[5]}/100")
            print(f"Penalty Score: {row[6]}")
            print(f"Source: {row[7]}")
            print(f"Title: {row[8]}")
            print(f"Company: {row[9]}")
            print(f"Location: {row[10]}")
            print(f"URL: {row[11]}")
            print(f"Matched Keywords: {row[12]}")
            print(f"Red Flags: {row[13]}")
            print(f"Recommendation: {row[14]}")
            print(f"Summary: {row[15]}")
            print("-" * 100)

    conn.close()


if __name__ == "__main__":
    view_job_scores()