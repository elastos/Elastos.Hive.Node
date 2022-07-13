# -*- coding: utf-8 -*-
"""
This is for files management, include file, file content, file properties, and dir management.
"""
import hashlib
import json
import logging
import os
import pickle
import platform
import shutil
from datetime import datetime
from pathlib import Path

from flask import request
from flask_rangerequest import RangeRequest

from src.modules.auth.user import UserManager
from src.settings import hive_setting
from src.utils.consts import COL_IPFS_FILES, COL_IPFS_FILES_IPFS_CID, DID, SIZE, COL_IPFS_FILES_SHA256, \
    COL_IPFS_FILES_PATH, USR_DID, APP_DID
from src.utils.db_client import cli
from src.utils_v1.common import deal_dir, get_file_md5_info, create_full_path_dir, gene_temp_file_name
from src.utils_v1.constants import CHUNK_SIZE, DID_INFO_DB_NAME, VAULT_SERVICE_COL, VAULT_SERVICE_MAX_STORAGE
from src.utils_v1.did_file_info import get_save_files_path, get_user_did_path, get_directory_size
from src.utils.http_exception import BadRequestException, VaultNotFoundException


class FileManager:
    def __init__(self):
        self._http = None
        self.ipfs_url = hive_setting.IPFS_NODE_URL
        self.ipfs_gateway_url = hive_setting.IPFS_GATEWAY_URL
        self.user_manager = UserManager()

    @property
    def http(self):
        if not self._http:
            from src.utils.http_client import HttpClient
            self._http = HttpClient()
        return self._http

    def get_vault_max_size(self, user_did):
        doc = cli.find_one_origin(DID_INFO_DB_NAME, VAULT_SERVICE_COL, {DID: user_did})
        if not doc:
            raise VaultNotFoundException('Vault not found for get max size.')
        return int(doc[VAULT_SERVICE_MAX_STORAGE])

    def get_file_checksum_list(self, root_path: Path) -> list:
        """
        :return [(name, checksum), ...]
        """
        return list() if not root_path.exists() else \
            [(md5[0], Path(md5[1]).relative_to(root_path).as_posix())
                for md5 in deal_dir(root_path.as_posix(), get_file_md5_info)]

    def get_hashes_by_lines(self, lines):
        hashes = list()
        for line in lines:
            if not line:
                continue
            parts = line.split(b',')
            hashes.append((int(parts[0].decode("utf-8")), parts[1].decode("utf-8")))
        return hashes

    def write_file_by_response(self, response, file_path: Path, is_temp=False):
        if not self.create_parent_dir(file_path):
            raise BadRequestException(f'Failed to create parent folder for file {file_path.name}')

        if is_temp:
            def on_save_to_temp(temp_file):
                self.write_file_by_response(response, temp_file)
            self.__save_with_temp_file(file_path, on_save_to_temp)
        else:
            with open(file_path.as_posix(), 'bw') as f:
                f.seek(0)
                for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)

    def write_file_by_request_stream(self, file_path: Path):
        if not self.create_parent_dir(file_path):
            raise BadRequestException(f'Failed to create parent directory to hold file {file_path.name}.')

        def on_save_to_temp(temp_file):
            with open(temp_file.as_posix(), "bw") as f:
                while True:
                    chunk = request.stream.read(CHUNK_SIZE)
                    if len(chunk) == 0:
                        break
                    f.write(chunk)

        self.__save_with_temp_file(file_path, on_save_to_temp)

    def write_file_by_rsync_data(self, data, file_path: Path):
        with open(file_path.as_posix(), "wb") as f:
            pickle.dump(data, f)

    def read_rsync_data_from_file(self, file_path: Path):
        with open(file_path.as_posix(), "rb") as f:
            return pickle.load(f)

    def create_parent_dir(self, file_path: Path):
        return self.create_dir(file_path.parent)

    def create_dir(self, path: Path):
        if not path.exists() and not create_full_path_dir(path):
            return False
        return True

    def __save_with_temp_file(self, file_path: Path, on_save_to_temp):
        temp_file = gene_temp_file_name()

        on_save_to_temp(temp_file)

        if file_path.exists():
            file_path.unlink()
        shutil.move(temp_file.as_posix(), file_path.as_posix())

    def delete_file(self, file_path: Path):
        if file_path.exists() and file_path.is_file():
            file_path.unlink()

    def ipfs_gen_cache_file_name(self, path: str):
        return path.replace('/', '_').replace('\\', '_')

    def ipfs_get_file_path(self, user_did, app_did, path: str):
        # name = self.ipfs_gen_cache_file_name(path)
        # cache_path = st_get_ipfs_cache_path(user_did)
        # return cache_path / name

        # INFO: change to vault files folder for keeping sync with v1.
        return get_save_files_path(user_did, app_did) / path

    def ipfs_get_cache_root(self, user_did):
        root = get_user_did_path(user_did) / 'cache'
        if not root.exists():
            self.create_dir(root)
        return root

    def ipfs_get_app_file_usage(self, db_name):
        if not cli.is_database_exists(db_name):
            return 0
        files = cli.find_many_origin(db_name, COL_IPFS_FILES, {}, throw_exception=False)
        if not files:
            return 0
        return sum(map(lambda f: f[SIZE], files))

    def get_file_content_sha256(self, file_path: Path):
        buf_size = 65536  # lets read stuff in 64kb chunks!
        sha = hashlib.sha256()
        with file_path.open('rb') as f:
            while True:
                data = f.read(buf_size)
                if not data:
                    break
                sha.update(data)
        return sha.hexdigest()

    def ipfs_uploading_file(self, user_did, app_did, path: str):
        file_path = self.ipfs_get_file_path(user_did, app_did, path)
        return self.ipfs_upload_file_from_path(file_path)

    def ipfs_get_cache_size(self, user_did):
        root = get_user_did_path(user_did) / 'cache'
        if not root.exists():
            return 0
        return get_directory_size(root.as_posix())

    def get_response_by_file_path(self, path: Path):
        size = path.stat().st_size
        with open(path.as_posix(), 'rb') as f:
            etag = RangeRequest.make_etag(f)
        return RangeRequest(open(path.as_posix(), 'rb'),
                            etag=etag,
                            last_modified=datetime.now(),
                            size=size).make_response()

    def ipfs_download_file_to_path(self, cid, path: Path, is_proxy=False, sha256=None, size=None):
        url = self.ipfs_gateway_url if is_proxy else self.ipfs_url
        response = self.http.post(f'{url}/api/v0/cat?arg={cid}', None, None, is_body=False, success_code=200)
        self.write_file_by_response(response, path)
        if size is not None:
            cid_size = path.stat().st_size
            if size != cid_size:
                return f'Failed to get file content with cid {cid}, size {size, cid_size}'
        if sha256:
            cid_sha256 = self.get_file_content_sha256(path)
            if sha256 != cid_sha256:
                return f'Failed to get file content with cid {cid}, sha256 {sha256, cid_sha256}'

    def ipfs_download_file_content(self, cid, is_proxy=False, sha256=None, size=None):
        temp_file = gene_temp_file_name()
        msg = fm.ipfs_download_file_to_path(cid, temp_file, is_proxy=is_proxy, sha256=sha256, size=size)
        if msg:
            temp_file.unlink()
            raise BadRequestException(msg)
        with temp_file.open() as f:
            metadata = json.load(f)
        temp_file.unlink()
        return metadata

    def ipfs_upload_file_from_path(self, path: Path):
        files = {'file': open(path.as_posix(), 'rb')}
        json_data = self.http.post(self.ipfs_url + '/api/v0/add', None, None,
                                   is_json=False, files=files, success_code=200)
        return json_data['Hash']

    def ipfs_local_exist_cid(self, cid):
        try:
            response = self.http.post(f'{self.ipfs_url}/api/v0/cat?arg={cid}', None, None, is_body=False, success_code=200)
            return True
        except BadRequestException as e:
            return False

    def ipfs_unpin_cid(self, cid):
        logging.info(f'[fm.ipfs_unpin_cid] Try to unpin {cid} in backup node.')

        if not self.ipfs_local_exist_cid(cid):
            return

        try:
            response = self.http.post(self.ipfs_url + f'/api/v0/pin/rm?arg=/ipfs/{cid}&recursive=true', None, None, is_body=False, success_code=200)
        except BadRequestException as e:
            # skip this error
            if 'not pinned or pinned indirectly' not in e.msg:
                raise e

    def get_file_cids(self, user_did):
        databases = cli.get_all_user_databases(user_did)
        total_size, cids = 0, set()
        for d in databases:
            docs = cli.find_many_origin(d, COL_IPFS_FILES, {USR_DID: user_did},
                                        create_on_absence=False, throw_exception=False)
            if docs:
                cids.update([doc[COL_IPFS_FILES_IPFS_CID] for doc in docs])
                total_size += sum([doc[SIZE] for doc in docs])
        return total_size, list(cids)

    def get_file_cid_metadatas(self, user_did):
        """ get all cid infos from user's vault """
        database_names = self.user_manager.get_database_names(user_did)
        total_size, cids = 0, list()
        for database_name in database_names:
            docs = cli.find_many_origin(database_name, COL_IPFS_FILES, {USR_DID: user_did},
                                        create_on_absence=False, throw_exception=False)
            for doc in docs:
                mt = self._get_cid_metadata_from_list(cids, doc)
                if mt:
                    mt['count'] += 1
                else:
                    cids.append({'cid': doc[COL_IPFS_FILES_IPFS_CID],
                                 'sha256': doc[COL_IPFS_FILES_SHA256],
                                 'size': int(doc[SIZE]),
                                 'count': 1})
            total_size += sum([doc[SIZE] for doc in docs])
        return total_size, cids

    def get_app_file_metadatas(self, user_did, app_did) -> list:
        result = []
        docs = cli.find_many(user_did, app_did, COL_IPFS_FILES,
                             {USR_DID: user_did, APP_DID: app_did}, throw_exception=False)
        for doc in docs:
            result.append({
                "path": doc[COL_IPFS_FILES_PATH],
                "sha256": doc[COL_IPFS_FILES_SHA256],
                "size": doc[SIZE],
                "cid": doc[COL_IPFS_FILES_IPFS_CID],
                "created": doc['created'],
                "modified": doc['modified']
            })
        return result

    def ipfs_pin_cid(self, cid):
        # INFO: IPFS does not support that one node directly pin file from other node.
        logging.info(f'[fm.ipfs_pin_cid] Try to pin {cid} in backup node.')
        temp_file = gene_temp_file_name()
        self.ipfs_download_file_to_path(cid, temp_file, is_proxy=True)
        logging.info(f'[fm.ipfs_pin_cid] Download file OK.')
        self.ipfs_upload_file_from_path(temp_file)
        logging.info(f'[fm.ipfs_pin_cid] Upload file OK.')
        size = temp_file.stat().st_size
        temp_file.unlink()
        return size

    def get_files_recursively(self, root_dir: Path):
        files = []

        def get_files(dir: Path, result: list):
            for file in dir.iterdir():
                if file.is_dir():
                    get_files(file, result)
                elif file.is_file():
                    result.append(file)

        get_files(root_dir, files)
        return files

    def _get_cid_metadata_from_list(self, cid_mts, file_mt):
        if not cid_mts:
            return None
        for mt in cid_mts:
            if mt['cid'] == file_mt[COL_IPFS_FILES_IPFS_CID]:
                if mt['sha256'] != file_mt[COL_IPFS_FILES_SHA256] or mt['size'] != int(file_mt[SIZE]):
                    logging.error(f'Found an unexpected file {file_mt[COL_IPFS_FILES_PATH]} with same CID, '
                                  f'but different sha256 or size.')
                return mt
        return None

    def get_file_ctime(self, path_to_file: str):
        """
        Try to get the date that a file was created, falling back to when it was
        last modified if that isn't possible.
        See http://stackoverflow.com/a/39501288/1709587 for explanation.
        """
        if platform.system() == 'Windows':
            return os.path.getctime(path_to_file)
        else:
            stat = os.stat(path_to_file)
            try:
                return stat.st_birthtime
            except AttributeError:
                # We're probably on Linux. No easy way to get creation dates here,
                # so we'll settle for when its content was last modified.
                return stat.st_mtime


fm = FileManager()
