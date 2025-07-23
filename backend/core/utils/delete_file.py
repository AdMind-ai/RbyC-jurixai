import os
import logging

logger = logging.getLogger(__name__)


def delete_file(path):
    """
    Attempts to delete the file at the given path. Logs an error if the file
    cannot be deleted due to permissions or if an unexpected error occurs.
    """
    try:
        os.remove(path)
    except FileNotFoundError:
        logger.debug(f"File not found, nothing to delete: {path}")
    except PermissionError:
        logger.exception(f"Permission denied when deleting file: {path}")
    except OSError as e:
        logger.exception(f"Error deleting file {path}: {e}")
