from scrapers.greenhouse_scraper import GreenhouseScraper


def main():

    scraper = GreenhouseScraper()

    jobs = scraper.start()

    print()

    print(
        f"Total jobs: {len(jobs)}"
    )

    print()

    for job in jobs[:10]:

        print(job.company)
        print(job.title)
        print(job.location)

        print("-" * 40)


if __name__ == "__main__":
    main()