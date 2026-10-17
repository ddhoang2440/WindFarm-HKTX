import logging
import sys
from src.config.settings import get_settings

settings = get_settings()

# Config root logger
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger instance."""
    return logging.getLogger(name)