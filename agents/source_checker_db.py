import csv
import os
import requests
import psycopg
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
SOURCES_FILE = BASE_DIR / "data" / "sources.csv"

BLOCK_KEYWORDS = [
    "captcha",
    "access denied",
    "blocked",
    "verify you are human",
    "unusual traffic",
    "bot detection",
    "cloudflare",
    "forbidden",
]

HEADERS = {
    "User-Agent": "AI-Job-Agent-Learning-Project/0.2"
}


def get_db_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def classify_response(status_code, response_text, headers=None):
    headers = headers or {}
    content_type = headers.get("Content-Type", "").lower()
    text = response_text.lower().strip()

    if status_code == 200:
        if "application/json" in content_type:
            return "accessible"

        if text.startswith("{") or text.startswith("["):
            return "accessible"

        for keyword in BLOCK_KEYWORDS:
            if keyword in text:
                return "blocked"

        return "accessible"

    if status_code in [401, 403]:
        return "restricted"

    if status_code == 404:
        return "not_found"

    if status_code == 429:
        return "rate_limited"

    if status_code >= 500:
        return "server_error"

    return "unknown"


def read_sources():
    with open(SOURCES_FILE, mode="r", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def upsert_job_source(conn, source):
    query = """
        INSERT INTO job_sources (
            source_name,
            source_url,
            source_type,
            target_role,
            status,
            notes
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (source_url)
        DO UPDATE SET
            source_name = EXCLUDED.source_name,
            source_type = EXCLUDED.source_type,
            target_role = EXCLUDED.target_role,
            status = EXCLUDED.status,
            notes = EXCLUDED.notes
        RETURNING id;
    """

    with conn.cursor() as cur:
        cur.execute(
            query,
            (
                source["source_name"],
                source["url"],
                source["source_type"],
                source["target_role"],
                source.get("status", "not_tested"),
                source.get("notes", ""),
            ),
        )
        return cur.fetchone()[0]


def save_check_result(conn, source_id, result):
    query = """
        INSERT INTO source_check_results (
            source_id,
            check_status,
            http_status_code,
            error_message,
            checked_at
        )
        VALUES (%s, %s, %s, %s, %s);
    """

    with conn.cursor() as cur:
        cur.execute(
            query,
            (
                source_id,
                result["check_status"],
                result["http_status_code"],
                result["error_message"],
                result["checked_at"],
            ),
        )


def build_error_result(status, message):
    return {
        "check_status": status,
        "http_status_code": None,
        "error_message": message,
        "checked_at": datetime.now(),
    }


def check_source(source):
    url = source["url"]

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=15
        )

        check_status = classify_response(
            response.status_code,
            response.text[:3000],
            response.headers
        )

        return {
            "check_status": check_status,
            "http_status_code": response.status_code,
            "error_message": "",
            "checked_at": datetime.now(),
        }

    except requests.exceptions.Timeout:
        return build_error_result("timeout", "Request timed out")

    except requests.exceptions.ConnectionError:
        return build_error_result("connection_error", "Connection failed")

    except Exception as error:
        return build_error_result("error", str(error))


def main():
    print("Starting source access check with PostgreSQL storage...")

    sources = read_sources()
    conn = get_db_connection()

    try:
        for source in sources:
            print(f"Checking: {source['source_name']}")

            source_id = upsert_job_source(conn, source)
            result = check_source(source)
            save_check_result(conn, source_id, result)

            print(
                f"Result: {result['check_status']} "
                f"HTTP: {result['http_status_code']}"
            )

        conn.commit()
        print("\nSource check completed.")
        print("Results saved to PostgreSQL.")

    except Exception as error:
        conn.rollback()
        print("Source check failed.")
        print(error)

    finally:
        conn.close()


if __name__ == "__main__":
    main()