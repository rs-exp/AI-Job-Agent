from utils.logger import get_logger


def main() -> None:
    logger = get_logger(__name__)

    logger.info("Logger test started")
    logger.warning("This is a warning test")
    logger.error("This is an error test")

    print("Logger test completed.")


if __name__ == "__main__":
    main()