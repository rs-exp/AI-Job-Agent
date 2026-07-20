from database.connection import DatabaseConnection
from services.job_normalizer import JobNormalizer


def main() -> None:
    database = DatabaseConnection()
    normalizer = JobNormalizer()

    select_query = """
        SELECT
            id,
            company,
            title,
            location
        FROM jobs
        WHERE fingerprint IS NULL
        ORDER BY id;
    """

    update_query = """
        UPDATE jobs
        SET
            fingerprint = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s;
    """

    with database.get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(select_query)
            rows = cursor.fetchall()

            if not rows:
                print("No missing fingerprints found.")
                return

            updates: list[tuple[str, int]] = []

            for job_id, company, title, location in rows:
                normalized_company = normalizer._clean_text(
                    company
                )
                normalized_title = normalizer._clean_text(
                    title
                )
                normalized_location = normalizer._clean_text(
                    location
                )

                if not normalized_location:
                    normalized_location = "Not specified"

                fingerprint = normalizer._generate_fingerprint(
                    company=normalized_company,
                    title=normalized_title,
                    location=normalized_location,
                )

                updates.append(
                    (
                        fingerprint,
                        job_id,
                    )
                )

            cursor.executemany(
                update_query,
                updates,
            )

            connection.commit()

    print(
        f"Backfilled fingerprints for "
        f"{len(updates)} historical jobs."
    )


if __name__ == "__main__":
    main()