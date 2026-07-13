import os
import psycopg
from dotenv import load_dotenv

load_dotenv()


def test_db_connection():
    try:
        conn = psycopg.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
        )

        with conn.cursor() as cur:
            cur.execute("SELECT current_database(), current_user;")
            database_name, user_name = cur.fetchone()

            print("Database connected successfully.")
            print(f"Database: {database_name}")
            print(f"User: {user_name}")

        conn.close()

    except Exception as error:
        print("Database connection failed.")
        print(error)


if __name__ == "__main__":
    test_db_connection()