import os
import psycopg
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
SCHEMA_FILE = BASE_DIR / "database" / "schema.sql"


def apply_schema():
    try:
        with open(SCHEMA_FILE, "r", encoding="utf-8") as file:
            schema_sql = file.read()

        conn = psycopg.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
        )

        with conn.cursor() as cur:
            cur.execute(schema_sql)

        conn.commit()
        conn.close()

        print("Database schema applied successfully.")

    except Exception as error:
        print("Failed to apply database schema.")
        print(error)


if __name__ == "__main__":
    apply_schema()