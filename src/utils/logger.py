import logging
import sys

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if not logger.handlers: #prevent duplicate
    stream_handler = logging.StreamHandler(sys.stdout)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    stream_handler.setFormatter(formatter)
    

    logger.handlers = [stream_handler]
