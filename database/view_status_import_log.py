import os

import psycopg
from dotenv import load_dotenv

load_dotenv()


def get_db_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def main():
    conn = get_db_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    detected_status,
                    COUNT(*)
                FROM application_status_import_log
                GROUP BY detected_status
                ORDER BY COUNT(*) DESC;
            """)
            print("Status Import Summary")
            print("-" * 100)
            for row in cur.fetchall():
                print(row)

            cur.execute("""
                SELECT
                    file_name,
                    sheet_name,
                    row_number,
                    detected_status,
                    title,
                    company_name,
                    matched_normalized_job_id,
                    match_method,
                    import_note,
                    created_at
                FROM application_status_import_log
                ORDER BY created_at DESC, id DESC
                LIMIT 30;
            """)
            print("\nLatest Status Import Log")
            print("-" * 100)
            for row in cur.fetchall():
                print(f"File: {row[0]}")
                print(f"Sheet: {row[1]}")
                print(f"Row: {row[2]}")
                print(f"Status: {row[3]}")
                print(f"Title: {row[4]}")
                print(f"Company: {row[5]}")
                print(f"Matched Job ID: {row[6]}")
                print(f"Match Method: {row[7]}")
                print(f"Note: {row[8]}")
                print(f"Created At: {row[9]}")
                print("-" * 100)

    finally:
        conn.close()


if __name__ == "__main__":
    main()