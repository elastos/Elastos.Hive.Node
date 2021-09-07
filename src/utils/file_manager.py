# -*- coding: utf-8 -*-

"""
This is for files management, include file, file content, file properties, and dir management.
"""
import hashlib
import pickle
import shutil
from datetime import datetime
from pathlib import Path

from flask import request

from src.settings import hive_setting
from src.utils.consts import COL_IPFS_FILES, COL_IPFS_FILES_IPFS_CID, DID, SIZE
from src.utils.db_client import cli
from src.utils_v1.common import deal_dir, get_file_md5_info, create_full_path_dir, gene_temp_file_name
from src.utils_v1.constants import CHUNK_SIZE, DID_INFO_DB_NAME, VAULT_SERVICE_COL, VAULT_SERVICE_MAX_STORAGE, \
    VAULT_SERVICE_FILE_USE_STORAGE, VAULT_SERVICE_DB_USE_STORAGE
from src.utils_v1.did_file_info import get_save_files_path
from src.utils_v1.flask_rangerequest import RangeRequest
from src.utils_v1.payment.vault_backup_service_manage import get_vault_backup_path
from src.utils_v1.payment.vault_service_manage import get_vault_used_storage
from src.utils_v1.pyrsync import rsyncdelta, gene_blockchecksums, patchstream
from src.utils.http_exception import BadRequestException, VaultNotFoundException
from src.utils.node_settings import st_get_ipfs_cache_path


class FileManager:
    def __init__(self):
        self._http = None
        self.ipfs_url = hive_setting.IPFS_NODE_URL

    @property
    def http(self):
        if not self._http:
            from src.utils.http_client import HttpClient
            self._http = HttpClient()
        return self._http

    def get_vault_storage_size(self, did):
        doc = cli.find_one_origin(DID_INFO_DB_NAME, VAULT_SERVICE_COL, {DID: did})
        if not doc:
            raise VaultNotFoundException(msg='Vault not found for get storage size.')
        return int(doc[VAULT_SERVICE_FILE_USE_STORAGE] + doc[VAULT_SERVICE_DB_USE_STORAGE])

    def get_vault_max_size(self, did):
        doc = cli.find_one_origin(DID_INFO_DB_NAME, VAULT_SERVICE_COL, {DID: did})
        if not doc:
            raise VaultNotFoundException(msg='Vault not found for get max size.')
        return int(doc[VAULT_SERVICE_MAX_STORAGE])

    def get_file_checksum_list(self, root_path: Path) -> list:
        """
        :return [(name, checksum), ...]
        """
        return list() if not root_path.exists() else \
            [(md5[0], Path(md5[1]).relative_to(root_path).as_posix())
                for md5 in deal_dir(root_path.as_posix(), get_file_md5_info)]

    def get_hashes_by_file(self, file_path: Path):
        if not file_path.exists():
            return ''
        hashes = ''
        with open(file_path.as_posix(), 'rb') as open_file:
            for h in gene_blockchecksums(open_file, blocksize=CHUNK_SIZE):
                hashes += h
        return hashes

    def get_hashes_by_lines(self, lines):
        hashes = list()
        for line in lines:
            if not line:
                continue
            parts = line.split(b',')
            hashes.append((int(parts[0].decode("utf-8")), parts[1].decode("utf-8")))
        return hashes

    def get_rsync_data(self, src_path: Path, target_hashes):
        with open(src_path.as_posix(), "rb") as f:
            patch_data = rsyncdelta(f, target_hashes, blocksize=CHUNK_SIZE)
        return pickle.dumps(patch_data)

    def apply_rsync_data(self, file_path: Path, data):
        def on_save_to_temp(temp_file):
            with open(file_path.as_posix(), "br") as f:
                with open(temp_file.as_posix(), "bw") as tmp_f:
                    f.seek(0)
                    patchstream(f, tmp_f, data)
        self.__save_with_temp_file(file_path, on_save_to_temp)

    def write_file_by_response(self, response, file_path: Path, is_temp=False):
        if not self.create_parent_dir(file_path):
            raise BadRequestException(msg=f'Failed to create parent folder for file {file_path.name}')

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
            raise BadRequestException(msg=f'Failed to create parent folder for file {file_path.name}.')

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

    def delete_vault_file(self, did, name):
        self.delete_file((get_vault_backup_path(did) / name).resolve())

    def ipfs_gen_cache_file_name(self, path: str):
        return path.replace('/', '_').replace('\\', '_')

    def ipfs_get_file_path(self, did, app_did, path: str):
        # name = self.ipfs_gen_cache_file_name(path)
        # cache_path = st_get_ipfs_cache_path(did)
        # return cache_path / name

        # INFO: change to vault files folder for keeping sync with v1.
        return get_save_files_path(did, app_did) / path

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

    def ipfs_uploading_file(self, did, app_did, path: str):
        file_path = self.ipfs_get_file_path(did, app_did, path)
        return self.ipfs_upload_file_from_path(file_path)

    def get_response_by_file_path(self, path: Path):
        size = path.stat().st_size
        with open(path.as_posix(), 'rb') as f:
            etag = RangeRequest.make_etag(f)
        return RangeRequest(open(path.as_posix(), 'rb'),
                            etag=etag,
                            last_modified=datetime.utcnow(),
                            size=size).make_response()

    def ipfs_download_file_to_path(self, cid, path: Path):
        response = self.http.post(self.ipfs_url + f'/api/v0/cat?arg={cid}', None, None, is_body=False, success_code=200)
        self.write_file_by_response(response, path)

    def ipfs_upload_file_from_path(self, path: Path):
        options = {'files': {'file': open(path.as_posix(), 'rb')}}
        json_data = self.http.post(self.ipfs_url + '/api/v0/add', None, None,
                                   is_json=False, options=options, success_code=200)
        return json_data['Hash']

    def ipfs_unpin_cid(self, cid):
        response = self.http.post(self.ipfs_url + f'/api/v0/pin/rm?arg=/ipfs/{cid}&recursive=true', None, None, is_body=False, success_code=200)

    def get_file_cids(self, did):
        databases = cli.get_all_user_databases(did)
        total_size, cids = 0, set()
        for d in databases:
            docs = cli.find_many_origin(d, COL_IPFS_FILES, {DID: did}, is_create=False, is_raise=False)
            if docs:
                cids.update([doc[COL_IPFS_FILES_IPFS_CID] for doc in docs])
                total_size += sum([doc[SIZE] for doc in docs])
        return total_size, list(cids)

    def ipfs_pin_cid(self, cid):
        # TODO: optimize this as ipfs not support pin other node file to local node.
        temp_file = gene_temp_file_name()
        self.ipfs_download_file_to_path(cid, temp_file)
        self.ipfs_upload_file_from_path(temp_file)
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


fm = FileManager()
