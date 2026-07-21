from __future__ import annotations

import logging
import sys

from config.settings import settings
from src.storage.database import db
from src.terminal.app import BloombergTerminal


def setup_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler("terminal.log"),
            logging.StreamHandler(sys.stderr),
        ],
    )


def main() -> None:
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("Starting Secure Bloomberg Terminal")
    logger.info("Config: log_level=%s db_path=%s", settings.log_level, settings.db_path)

    try:
        db.initialize()
        logger.info("Database initialized at %s", settings.db_path)
    except Exception as e:
        logger.warning("Database initialization skipped: %s", e)

    app = BloombergTerminal()

    try:
        app.run()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.critical("Fatal error: %s", e, exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Bloomberg Terminal terminated")


if __name__ == "__main__":
    main()
