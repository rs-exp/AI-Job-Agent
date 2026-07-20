from scrapers.arbeitnow_scraper import ArbeitNowScraper


def main() -> None:
    scraper = ArbeitNowScraper()

    jobs = scraper.start()

    print(f"\nTotal jobs received: {len(jobs)}\n")

    for job in jobs[:5]:
        print(f"Title     : {job.title}")
        print(f"Company   : {job.company}")
        print(f"Location  : {job.location}")
        print(f"Remote    : {job.remote}")
        print("-" * 50)


if __name__ == "__main__":
    main()