from database.job_repository import JobRepository
from scrapers.remotive_scraper import RemotiveScraper


def main() -> None:
    scraper = RemotiveScraper()
    repository = JobRepository()

    jobs = scraper.start()

    inserted, duplicates, failed = repository.save_jobs(jobs)
    total_in_database = repository.count_jobs()

    print("\nDatabase save completed")
    print(f"Received:          {len(jobs)}")
    print(f"Inserted:          {inserted}")
    print(f"Duplicates:        {duplicates}")
    print(f"Failed:            {failed}")
    print(f"Total in database: {total_in_database}")


if __name__ == "__main__":
    main()