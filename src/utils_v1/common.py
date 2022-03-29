import logging
import os
import random
from pathlib import Path
from urllib.parse import urlparse
import hashlib

from src.settings import hive_setting


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


def get_temp_path():
    path = Path(hive_setting.DATA_STORE_PATH).resolve() / ".temp/"
    if not path.exists():
        create_full_path_dir(path)
    return path


def gene_temp_file_name():
    temp_path = get_temp_path()
    while True:
        patch_delta_file = temp_path / random_string(10)
        if not patch_delta_file.exists():
            return patch_delta_file


def get_file_md5_info(file_name):
    m = hashlib.md5()
    with open(file_name, 'rb') as f:
        while True:
            chunk = f.read(4)
            if not chunk:
                break
            m.update(chunk)
    return [m.hexdigest(), file_name]


def deal_dir(dir_path, deal_func):
    path = Path(dir_path).resolve()
    if not path.exists():
        return

    file_list = os.listdir(path.as_posix())
    for i in file_list:
        i_path = path / i
        if i_path.is_dir():
            try:
                yield from deal_dir(i_path.as_posix(), deal_func)
            except RecursionError:
                logging.getLogger("Hive_Node").error("Err: get_dir_size too much for get_file_size")
        else:
            yield deal_func(i_path.as_posix())


def get_file_checksum_list(folder):
    checksum_list = list()
    local_file_gene = deal_dir(folder.as_posix(), get_file_md5_info)
    for info in local_file_gene:
        checksum_list.append(info[0])
    return checksum_list
