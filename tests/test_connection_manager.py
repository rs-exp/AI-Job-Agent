from database.connection import DatabaseConnection


def main() -> None:
    db = DatabaseConnection()

    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            version = cur.fetchone()

            print("\nConnected successfully\n")
            print(version[0])


if __name__ == "__main__":
    main()