from ._request import RangeRequest
import logging

# Set up logging
logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.DEBUG,
    datefmt='%Y-%m-%d %H:%M:%S'
)

__version__ = '0.0.0'

__all__ = ['RangeRequest']
