import logging
import random
from urllib.parse import urlparse


def did_tail_part(did):
    return did.split(":")[2]


def create_full_path_dir(path):
    try:
        path.mkdir(exist_ok=True, parents=True)
    except Exception as e:
        logging.debug(f"Exception in create_full_path: {e}")
        return False
    return True


def random_string(num):
    return "".join(random.sample('zyxwvutsrqponmlkjihgfedcba', num))


def get_host(url):
    data = urlparse(url)
    return data.hostname
