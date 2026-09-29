import logging

from shared.config import get_settings


def configure_logging() -> None:
    logging.basicConfig(
        level=get_settings().log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
