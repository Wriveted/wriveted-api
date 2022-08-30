import logging

from tenacity import after_log, before_log, retry, stop_after_attempt, wait_fixed

from app.config import get_settings
from app.db.session import get_session_maker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

max_tries = 60 * 5  # 5 minutes
wait_seconds = 1


@retry(
    stop=stop_after_attempt(max_tries),
    wait=wait_fixed(wait_seconds),
    before=before_log(logger, logging.DEBUG),
    after=after_log(logger, logging.INFO),
)
def check_can_connect_to_database() -> None:
    session_maker = get_session_maker()
    session = session_maker()
    logger.debug(f"Session: {session}")
    try:
        logger.debug("Checking DB is awake and accepting connections")
        session.execute("SELECT 1")
        logger.info("Database is responding to queries")
    except Exception as e:
        logger.error(e)
        raise e


def check_database_ready_with_retry(config):
    logger.info("Waiting for database to accept connections")
    logger.info(config)
    check_can_connect_to_database()
    logger.info("Database ready")


if __name__ == "__main__":
    config = get_settings()
    check_database_ready_with_retry(config)
