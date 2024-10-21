import logging
from functools import wraps


# logging.basicConfig()
logging.basicConfig(level=logging.WARN,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set the logging level for main flask app
logger.setLevel(logging.INFO)

# Set the logging level for sqlalchemy
# logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
logging.getLogger('sqlalchemy.engine').setLevel(logging.ERROR)

# Set the logging level for Werkzeug
# logging.getLogger('werkzeug').setLevel(logging.ERROR)
# logging.getLogger('werkzeug').setLevel(logging.WARNING)
logging.getLogger('werkzeug').setLevel(logging.INFO)


def log_function_call(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.info(f"Entering: {func.__name__}")
        result = func(*args, **kwargs)
        logger.info(f"Exiting: {func.__name__}")
        return result
    return wrapper
