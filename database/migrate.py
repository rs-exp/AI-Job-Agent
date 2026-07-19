import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
MIGRATIONS_DIR = BASE_DIR / "migrations"


CREATE_MIGRATION_TABLE = """
    CREATE TABLE IF NOT EXISTS schema_migrations (
        migration_name TEXT PRIMARY KEY,
        applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
"""


def get_connection() -> psycopg.Connection:
    """
    Create a PostgreSQL connection from environment variables.
    """

    return psycopg.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def run_migrations() -> None:
    """
    Apply pending SQL migrations in filename order.
    """

    migration_files = sorted(
        MIGRATIONS_DIR.glob("*.sql")
    )

    if not migration_files:
        print("No migration files found.")
        return

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(CREATE_MIGRATION_TABLE)
            connection.commit()

            for migration_file in migration_files:
                migration_name = migration_file.name

                cursor.execute(
                    """
                    SELECT 1
                    FROM schema_migrations
                    WHERE migration_name = %s;
                    """,
                    (migration_name,),
                )

                if cursor.fetchone():
                    print(
                        f"Skipped: {migration_name} "
                        "(already applied)"
                    )
                    continue

                migration_sql = migration_file.read_text(
                    encoding="utf-8"
                )

                try:
                    cursor.execute(migration_sql)

                    cursor.execute(
                        """
                        INSERT INTO schema_migrations (
                            migration_name
                        )
                        VALUES (%s);
                        """,
                        (migration_name,),
                    )

                    connection.commit()

                    print(f"Applied: {migration_name}")

                except Exception:
                    connection.rollback()

                    print(f"Failed: {migration_name}")
                    raise

    print("Database migrations completed.")


if __name__ == "__main__":
    run_migrations()