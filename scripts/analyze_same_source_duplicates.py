from database.connection import DatabaseConnection


def main() -> None:
    database = DatabaseConnection()

    query = """
        WITH duplicate_fingerprints AS (
            SELECT
                fingerprint,
                source,
                COUNT(*) AS job_count
            FROM jobs
            WHERE fingerprint IS NOT NULL
            GROUP BY fingerprint, source
            HAVING COUNT(*) > 1
        )
        SELECT
            duplicates.fingerprint,
            duplicates.source,
            duplicates.job_count,
            jobs.id,
            jobs.company,
            jobs.title,
            jobs.location,
            jobs.employment_type,
            jobs.posted_date,
            jobs.created_at,
            jobs.url
        FROM duplicate_fingerprints AS duplicates
        JOIN jobs
            ON jobs.fingerprint = duplicates.fingerprint
           AND jobs.source = duplicates.source
        ORDER BY
            duplicates.job_count DESC,
            duplicates.source,
            duplicates.fingerprint,
            jobs.id;
    """

    with database.get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()

    print("=" * 80)
    print("SAME-SOURCE FINGERPRINT DUPLICATE ANALYSIS")
    print("=" * 80)

    if not rows:
        print("No same-source fingerprint duplicates found.")
        return

    current_group = None
    group_number = 0

    for row in rows:
        (
            fingerprint,
            source,
            job_count,
            job_id,
            company,
            title,
            location,
            employment_type,
            posted_date,
            created_at,
            url,
        ) = row

        group_key = (fingerprint, source)

        if group_key != current_group:
            current_group = group_key
            group_number += 1

            print("\n" + "-" * 80)
            print(
                f"Group {group_number} | "
                f"Source: {source} | Jobs: {job_count}"
            )
            print(f"Fingerprint: {fingerprint}")
            print("-" * 80)

        print(f"ID:              {job_id}")
        print(f"Company:         {company}")
        print(f"Title:           {title}")
        print(f"Location:        {location}")
        print(f"Employment type: {employment_type}")
        print(f"Posted date:     {posted_date}")
        print(f"Created at:      {created_at}")
        print(f"URL:             {url}")
        print()

    print("=" * 80)
    print(f"Duplicate groups displayed: {group_number}")
    print("=" * 80)


if __name__ == "__main__":
    main()