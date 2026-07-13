import os
import psycopg
from dotenv import load_dotenv

load_dotenv()


def verify_tables():
    try:
        conn = psycopg.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
        )

        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)

            tables = cur.fetchall()

            print("Tables found:")
            for table in tables:
                print(f"- {table[0]}")

        conn.close()

    except Exception as error:
        print("Failed to verify tables.")
        print(error)


if __name__ == "__main__":
    verify_tables()