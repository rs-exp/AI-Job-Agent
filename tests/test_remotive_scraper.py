from scrapers.remotive_scraper import RemotiveScraper


def main() -> None:
    scraper = RemotiveScraper()
    jobs = scraper.start()

    print(f"\nTotal jobs received: {len(jobs)}\n")

    for job in jobs[:5]:
        print(f"Title: {job.title}")
        print(f"Company: {job.company}")
        print(f"Location: {job.location}")
        print(f"URL: {job.url}")
        print("-" * 60)


if __name__ == "__main__":
    main()