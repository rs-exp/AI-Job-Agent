import os
import psycopg
from dotenv import load_dotenv

load_dotenv()


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
            js.role_score,
            js.skill_score,
            js.experience_score,
            js.location_score,
            js.penalty_score,
            j.title,
            j.company_name,
            j.location,
            j.job_url,
            js.matched_keywords,
            js.red_flags,
            js.score_summary
        FROM job_scores js
        JOIN jobs_normalized j
            ON js.normalized_job_id = j.id
        WHERE js.scoring_version = 'rule_v0.1'
        ORDER BY js.overall_score DESC, js.skill_score DESC
        LIMIT 10;
    """

    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()

        print("Top scored jobs:")
        print("-" * 100)

        for row in rows:
            print(f"Overall Score: {row[0]}/100")
            print(f"Role Score: {row[1]}/100")
            print(f"Skill Score: {row[2]}/100")
            print(f"Experience Score: {row[3]}/100")
            print(f"Location Score: {row[4]}/100")
            print(f"Penalty Score: {row[5]}")
            print(f"Title: {row[6]}")
            print(f"Company: {row[7]}")
            print(f"Location: {row[8]}")
            print(f"URL: {row[9]}")
            print(f"Matched Keywords: {row[10]}")
            print(f"Red Flags: {row[11]}")
            print(f"Summary: {row[12]}")
            print("-" * 100)

    conn.close()


if __name__ == "__main__":
    view_job_scores()