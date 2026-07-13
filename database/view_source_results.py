import os
import psycopg
from dotenv import load_dotenv

load_dotenv()


def view_source_results():
    conn = psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )

    query = """
        SELECT
            js.source_name,
            js.source_type,
            js.target_role,
            scr.check_status,
            scr.http_status_code,
            scr.checked_at
        FROM source_check_results scr
        JOIN job_sources js
            ON scr.source_id = js.id
        ORDER BY scr.checked_at DESC
        LIMIT 10;
    """

    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()

        print("Latest source check results:")
        print("-" * 80)

        for row in rows:
            print(
                f"Source: {row[0]} | "
                f"Type: {row[1]} | "
                f"Role: {row[2]} | "
                f"Status: {row[3]} | "
                f"HTTP: {row[4]} | "
                f"Checked At: {row[5]}"
            )

    conn.close()


if __name__ == "__main__":
    view_source_results()