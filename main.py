from agents.collector import JobCollector
from utils.logger import get_logger


logger = get_logger(__name__)


def main() -> None:
    logger.info("AI Job Agent started.")

    collector = JobCollector()
    summary = collector.run()

    print()
    print("=" * 50)
    print("AI JOB AGENT - COLLECTION SUMMARY")
    print("=" * 50)
    print(f"Sources run:       {summary.sources_run}")
    print(f"Jobs received:     {summary.jobs_received}")
    print(f"Jobs inserted:     {summary.jobs_inserted}")
    print(f"Jobs updated:      {summary.jobs_updated}")
    print(f"Relevant jobs:     {summary.relevant_jobs}")
    print(f"Non-relevant jobs: {summary.non_relevant_jobs}")
    print(f"Duplicates:        {summary.duplicates}")
    print(f"Failed jobs:       {summary.failed_jobs}")
    print(f"Failed sources:    {summary.failed_sources}")
    print(
        f"Execution time:    "
        f"{summary.execution_time_seconds} seconds"
    )
    print("=" * 50)

    if summary.failed_sources or summary.failed_jobs:
        logger.warning(
            "AI Job Agent completed with some failures."
        )
    else:
        logger.info(
            "AI Job Agent completed successfully."
        )


if __name__ == "__main__":
    main()