import random
from pathlib import Path

from src import hive_setting


class LocalFile:
    def __init__(self):
        ...

    @staticmethod
    def generate_tmp_file() -> Path:
        """ get temp file path which not exists """

        tmp_dir = Path(hive_setting.get_temp_dir())
        if not tmp_dir.exists():
            tmp_dir.mkdir(exist_ok=True, parents=True)

        def random_string(num):
            return "".join(random.sample('zyxwvutsrqponmlkjihgfedcba', num))

        while True:
            patch_delta_file = tmp_dir / random_string(10)
            if not patch_delta_file.exists():
                return patch_delta_file

    @classmethod
    def remove_ipfs_cache_file(cls, user_did, cid):
        """ remove cid related cache file if exists """

        cache_file = hive_setting.get_user_did_path(user_did) / cid
        if cache_file.exists():
            cache_file.unlink()
