import logging
import random


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
    return random.sample('zyxwvutsrqponmlkjihgfedcba', num)
