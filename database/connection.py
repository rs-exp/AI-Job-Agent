import os
from contextlib import contextmanager
from pathlib import Path

import psycopg
from dotenv import load_dotenv

from utils.logger import get_logger

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(dotenv_path=ENV_FILE)

logger = get_logger(__name__)


class DatabaseConnection:
    """
    PostgreSQL connection manager.
    """

    def __init__(self) -> None:
        self.db_host = os.getenv("DB_HOST")
        self.db_port = os.getenv("DB_PORT")
        self.db_name = os.getenv("DB_NAME")
        self.db_user = os.getenv("DB_USER")
        self.db_password = os.getenv("DB_PASSWORD")

        required_variables = {
            "DB_HOST": self.db_host,
            "DB_PORT": self.db_port,
            "DB_NAME": self.db_name,
            "DB_USER": self.db_user,
            "DB_PASSWORD": self.db_password,
        }

        missing_variables = [
            name for name, value in required_variables.items() if not value
        ]

        if missing_variables:
            raise ValueError(
                "Missing environment variables: "
                + ", ".join(missing_variables)
            )

        self.connection_string = (
            f"host={self.db_host} "
            f"port={self.db_port} "
            f"dbname={self.db_name} "
            f"user={self.db_user} "
            f"password={self.db_password}"
        )

    @contextmanager
    def get_connection(self):
        connection = None

        try:
            connection = psycopg.connect(self.connection_string)
            logger.info("Connected to PostgreSQL.")

            yield connection

        except Exception as error:
            logger.error("Database operation failed: %s", error)
            raise

        finally:
            if connection is not None:
                connection.close()
                logger.info("Database connection closed.")