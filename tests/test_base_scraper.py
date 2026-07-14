from scrapers.dummy_scraper import DummyScraper


def main():

    scraper = DummyScraper()

    jobs = scraper.start()

    print()

    print(f"Total Jobs : {len(jobs)}")

    print()

    for job in jobs:

        print(job.title)
        print(job.company)
        print(job.location)
        print("-" * 40)


if __name__ == "__main__":
    main()