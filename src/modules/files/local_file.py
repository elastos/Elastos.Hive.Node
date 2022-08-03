import hashlib
import random
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from flask import request
from flask_rangerequest import RangeRequest

from src import hive_setting
from src.utils.http_exception import BadRequestException
from src.utils_v1.constants import CHUNK_SIZE


class LocalFile:
    def __init__(self):
        ...

    @staticmethod
    def generate_tmp_file_path() -> Path:
        """ get temp file path which not exists """

        tmp_dir = Path(hive_setting.get_temp_dir())
        LocalFile.create_dir_if_not_exists(tmp_dir)

        def random_string(num):
            return "".join(random.sample('zyxwvutsrqponmlkjihgfedcba', num))

        while True:
            patch_delta_file = tmp_dir / random_string(10)
            if not patch_delta_file.exists():
                return patch_delta_file

    @staticmethod
    def create_dir_if_not_exists(dir_path: Path):
        if not dir_path.exists():
            dir_path.mkdir(exist_ok=True, parents=True)

    @staticmethod
    def get_cid_cache_dir(user_did, need_create=False) -> Path:
        cache_dir = hive_setting.get_user_did_path(user_did) / 'cache'
        if need_create:
            LocalFile.create_dir_if_not_exists(cache_dir)
        return cache_dir

    @staticmethod
    def remove_ipfs_cache_file(user_did, cid):
        """ remove cid related cache file if exists """

        cache_file = LocalFile.get_cid_cache_dir(user_did) / cid
        if cache_file.exists():
            cache_file.unlink()

    @staticmethod
    def get_sha256(file_path: str) -> str:
        """ get sha256 of the local file content """

        buf_size = 65536  # lets read stuff in 64kb chunks!
        sha = hashlib.sha256()
        with open(file_path, 'rb') as f:
            while True:
                data = f.read(buf_size)
                if not data:
                    break
                sha.update(data)
        return sha.hexdigest()

    @staticmethod
    def write_file_by_request_stream(file_path: Path):
        """ used when upload file to this node """

        # create base folder
        LocalFile.create_dir_if_not_exists(file_path.parent)

        # write stream to temporary file
        temp_file = LocalFile.generate_tmp_file_path()

        with open(temp_file.as_posix(), "bw") as f:
            while True:
                chunk = request.stream.read(CHUNK_SIZE)
                if len(chunk) == 0:
                    break
                f.write(chunk)

        # move temp file to target path
        if file_path.exists():
            file_path.unlink()
        shutil.move(temp_file.as_posix(), file_path.as_posix())

    @staticmethod
    def write_file_by_response(response, file_path: Path):
        """ used when download file by url """

        # create base folder
        LocalFile.create_dir_if_not_exists(file_path.parent)

        with open(file_path.as_posix(), 'bw') as f:
            f.seek(0)
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    f.write(chunk)

    @staticmethod
    def get_download_response(file_path: Path):
        """ get download response for the API of this node. """
        size = file_path.stat().st_size
        with open(file_path.as_posix(), 'rb') as f:
            etag = RangeRequest.make_etag(f)
        return RangeRequest(open(file_path.as_posix(), 'rb'),
                            etag=etag,
                            last_modified=datetime.now(),
                            size=size).make_response()

    @staticmethod
    def dump_mongodb_to_full_path(db_name, full_path: Path):
        try:
            line2 = f'mongodump --uri="{hive_setting.MONGODB_URI}" -d {db_name} --archive="{full_path.as_posix()}"'
            subprocess.check_output(line2, shell=True, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            raise BadRequestException(f'Failed to dump database {db_name}: {e.output}')

    @staticmethod
    def restore_mongodb_from_full_path(full_path: Path):
        if not full_path.exists():
            raise BadRequestException(f'Failed to import mongo db by invalid full dir {full_path.as_posix()}')

        try:
            # https://www.mongodb.com/docs/database-tools/mongorestore/#cmdoption--drop
            # --drop: drop collections before restore, but does not drop collections that are not in the backup.
            line2 = f'mongorestore --uri="{hive_setting.MONGODB_URI}" --drop --archive="{full_path.as_posix()}"'
            subprocess.check_output(line2, shell=True, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            raise BadRequestException(f'Failed to load database by {full_path.as_posix()}: {e.output}')
