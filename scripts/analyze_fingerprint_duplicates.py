from database.connection import DatabaseConnection


def main() -> None:
    database = DatabaseConnection()

    summary_query = """
        SELECT
            COUNT(*) AS total_jobs,
            COUNT(fingerprint) AS fingerprinted_jobs,
            COUNT(*) FILTER (
                WHERE fingerprint IS NULL
            ) AS missing_fingerprints,
            COUNT(DISTINCT fingerprint) FILTER (
                WHERE fingerprint IS NOT NULL
            ) AS unique_fingerprints
        FROM jobs;
    """

    duplicate_summary_query = """
        SELECT
            COUNT(*) AS duplicate_groups,
            COALESCE(SUM(job_count), 0) AS jobs_in_duplicate_groups
        FROM (
            SELECT
                fingerprint,
                COUNT(*) AS job_count
            FROM jobs
            WHERE fingerprint IS NOT NULL
            GROUP BY fingerprint
            HAVING COUNT(*) > 1
        ) AS duplicate_fingerprints;
    """

    cross_source_summary_query = """
        SELECT
            COUNT(*) AS cross_source_groups,
            COALESCE(SUM(job_count), 0) AS jobs_in_cross_source_groups
        FROM (
            SELECT
                fingerprint,
                COUNT(*) AS job_count
            FROM jobs
            WHERE fingerprint IS NOT NULL
            GROUP BY fingerprint
            HAVING COUNT(DISTINCT source) > 1
        ) AS cross_source_fingerprints;
    """

    cross_source_details_query = """
        WITH duplicate_fingerprints AS (
            SELECT
                fingerprint,
                COUNT(*) AS job_count,
                COUNT(DISTINCT source) AS source_count
            FROM jobs
            WHERE fingerprint IS NOT NULL
            GROUP BY fingerprint
            HAVING COUNT(DISTINCT source) > 1
        )
        SELECT
            duplicate_fingerprints.fingerprint,
            duplicate_fingerprints.job_count,
            duplicate_fingerprints.source_count,
            jobs.source,
            jobs.company,
            jobs.title,
            jobs.location,
            jobs.url
        FROM duplicate_fingerprints
        JOIN jobs
            ON jobs.fingerprint =
               duplicate_fingerprints.fingerprint
        ORDER BY
            duplicate_fingerprints.source_count DESC,
            duplicate_fingerprints.job_count DESC,
            duplicate_fingerprints.fingerprint,
            jobs.source,
            jobs.id
        LIMIT 200;
    """

    with database.get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(summary_query)
            summary = cursor.fetchone()

            cursor.execute(duplicate_summary_query)
            duplicate_summary = cursor.fetchone()

            cursor.execute(cross_source_summary_query)
            cross_source_summary = cursor.fetchone()

            cursor.execute(cross_source_details_query)
            cross_source_rows = cursor.fetchall()

    print("=" * 70)
    print("JOB FINGERPRINT ANALYSIS")
    print("=" * 70)
    print(f"Total jobs:                    {summary[0]}")
    print(f"Jobs with fingerprints:        {summary[1]}")
    print(f"Jobs missing fingerprints:     {summary[2]}")
    print(f"Unique fingerprints:           {summary[3]}")
    print()
    print(f"All duplicate groups:          {duplicate_summary[0]}")
    print(f"Jobs in duplicate groups:      {duplicate_summary[1]}")
    print(f"Cross-source duplicate groups: {cross_source_summary[0]}")
    print(f"Jobs in cross-source groups:   {cross_source_summary[1]}")
    print("=" * 70)

    if not cross_source_rows:
        print("\nNo cross-source duplicate fingerprints found.")
        return

    current_fingerprint = None

    for row in cross_source_rows:
        (
            fingerprint,
            job_count,
            source_count,
            source,
            company,
            title,
            location,
            url,
        ) = row

        if fingerprint != current_fingerprint:
            current_fingerprint = fingerprint

            print("\n" + "-" * 70)
            print(f"Fingerprint: {fingerprint}")
            print(
                f"Jobs: {job_count} | "
                f"Sources: {source_count}"
            )
            print("-" * 70)

        print(f"Source:   {source}")
        print(f"Company:  {company}")
        print(f"Title:    {title}")
        print(f"Location: {location}")
        print(f"URL:      {url}")
        print()


if __name__ == "__main__":
    main()