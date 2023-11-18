import os
import sys
import traceback
from logging import handlers
from django.conf import settings

# Initialize the project, build and new detailed loggers
project_logger = __import__('logging').getLogger(__name__)
build_logger = __import__('logging').getLogger('build_process')
detailed_logger = __import__('logging').getLogger('detailed')

# Load settings from configuration file
conf = settings.LOGGING
LOGGING_HOST = conf.get('LOGGING_HOST', 'localhost')
LOGGING_PORT = conf.get('LOGGING_PORT', 514)

# Papertrail specific settings
PAPERTRAIL_HOST = conf.get('PAPERTRAIL_HOST', 'logs.papertrailapp.com')
PAPERTRAIL_PORT = conf.get('PAPERTRAIL_PORT', 12345) 

# Error handling for logging setup
try:
    # Setup handler with server info using SysLogHandler
    handler = handlers.SysLogHandler(address=(PAPERTRAIL_HOST, PAPERTRAIL_PORT))

    # Using a precise and clear formatter for better understanding
    # NOTE: The old way of calling logging.Formatter will not be supported in Python 3.2+
    # Must import logging and use logging.Formatter
    import logging
    formatter = logging.Formatter('%(asctime)s - %(name)s [%(levelname)s] - %(message)s %(funcName)s %(pathname)s %(lineno)d', datefmt='%m/%d/%Y %I:%M:%S %p')
    handler.setFormatter(formatter)

    # Adding configured handler to the project, build and detailed loggers
    project_logger.addHandler(handler)
    build_logger.addHandler(handler)
    detailed_logger.addHandler(handler)

    # Configuring levels for loggers for more detailed logging
    # As above, in Python 3.2+ we should import logging directly
    project_logger.setLevel(logging.DEBUG)
    build_logger.setLevel(logging.INFO)
    detailed_logger.setLevel(logging.DEBUG)
except Exception as e:
    project_logger.error('An error occurred while setting up the logger and formatter.', exc_info=True)

# Error handling for applying logger configuration
try:
    # As above, in Python 3.2+ we should import logging directly
    logging.config.dictConfig(conf)
except Exception as e:
    project_logger.error('An error occurred while applying the configuration to the logger. Error: %s', e, exc_info=True)

def handle_worktree_change_error(error_message: str):
    """
    :param error_message: Error message for the worktree change
    """
    detailed_logger.error('Worktree contains unstaged changes. Exact Error: %s', error_message, exc_info=True)

def log_pactflow_response(headers: dict, body: str) -> None:
    """
    The purpose of this function is to log the Pactflow response headers and body.
    :param headers: These are the response headers received
    :param body: This is the response body received
    """
    try:
        detailed_logger.info('Pactflow Response Headers: %s', str(headers))
        detailed_logger.info('Pactflow Response Body: %s', body)
    except Exception as e:
        detailed_logger.error('An error occurred during the logging of pactflow response.', exc_info=True)

def log_build_process(msg: str, level: str = 'info') -> None:
    """
    Function to log the build process at the specific level.
    :param msg: String message to be logged
    :param level: Logging level (default='info')
    """
    try:
        if log_func := getattr(build_logger, level, None):
            log_func(msg)
        else:
            build_logger.info(msg)
    except Exception as e:
        detailed_logger.error('An error occurred during the logging of build process.', exc_info=True)

def log_execution_details(func):
    """
    This is a modified decorator function to log detailed execution information of the decorated function.
    :param func: The function for which execution details are logged
    """
    def wrapper(*args, **kwargs):
        detailed_logger.info('Function %s called with args: %s, and kwargs: %s', func.__name__, args, kwargs)
        detailed_logger.info('Running function %s...', func.__name__)

        try:
            result = func(*args, **kwargs)
            detailed_logger.info('Function %s executed successfully.', func.__name__)
            return result
        except Exception as e:
            detailed_logger.error('An error occurred while running function %s.', func.__name__, exc_info=True)
            tb = traceback.format_exc()
            detailed_logger.error(f"Traceback:\n {tb}")
            raise e
    return wrapper

def uncaught_exception_handler(type, value, tb):
    """
    This function is to handle uncaught exceptions and log them
    :param type: Exception Type
    :param value: Exception Value
    :param tb: Traceback
    """
    detailed_logger.error('Uncaught exception: {0}'.format(str(value)))
    tb = traceback.format_exception(type, value, tb)  # traceback.format_traceback will not work with Python 3.5+
    detailed_logger.error('Traceback: {0}'.format(''.join(tb)))

# Sets the function "uncaught_exception_handler" as the handler for unhandled exceptions
sys.excepthook = uncaught_exception_handler