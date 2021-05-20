# -*- coding: utf-8 -*-

"""
The entrance for files module.
"""
import os
import shutil

from flask import request

from hive.util.common import gene_temp_file_name
from hive.util.constants import VAULT_ACCESS_WR, CHUNK_SIZE, VAULT_ACCESS_R
from hive.util.did_file_info import query_upload_get_filepath, query_download, filter_path_root, get_save_files_path, \
    get_dir_size, query_hash
from hive.util.error_code import BAD_REQUEST, NOT_FOUND, FORBIDDEN
from hive.util.payment.vault_service_manage import inc_vault_file_use_storage_byte
from src.modules.scripting.scripting import check_auth_and_vault
from src.utils.http_response import BadRequestException


class Files:
    def __init__(self):
        pass

    def _get_file_full_path(self, did, app_did, path):
        fixed_path = filter_path_root(path)
        return (get_save_files_path(did, app_did) / fixed_path).resolve()

    def upload_file(self, path):
        did, app_did = check_auth_and_vault(VAULT_ACCESS_WR)
        full_path = self._upload_file_from_request_stream(did, app_did, path)
        inc_vault_file_use_storage_byte(did, os.path.getsize(full_path.as_posix()))
        return {
            'name': path
        }

    def _upload_file_from_request_stream(self, did, app_did, path):
        full_path, err = query_upload_get_filepath(did, app_did, path)
        if err:
            raise BadRequestException(msg=f'Failed to get upload file full path: "{str(err)}"')

        temp_file = self._upload_file2temp()
        if full_path.exists():
            full_path.unlink()
        shutil.move(temp_file.as_posix(), full_path.as_posix())

        return full_path

    def _upload_file2temp(self):
        temp_file = gene_temp_file_name()
        try:
            with open(temp_file, "bw") as f:
                while True:
                    chunk = request.stream.read(CHUNK_SIZE)
                    if len(chunk) == 0:
                        break
                    f.write(chunk)
        except Exception as e:
            raise BadRequestException(msg='Failed to write to upload file.')
        return temp_file

    def download_file(self, path):
        did, app_did = check_auth_and_vault(VAULT_ACCESS_R)
        data, status_code = query_download(did, app_did, path)
        if status_code == BAD_REQUEST:
            raise BadRequestException(msg='Cannot get file name by transaction id')
        elif status_code == NOT_FOUND:
            raise BadRequestException(msg=f"The file '{path}' does not exist.")
        elif status_code == FORBIDDEN:
            raise BadRequestException(msg=f"Cannot access the file '{path}'.")
        return data

    def delete_file(self, path):
        did, app_did = check_auth_and_vault(VAULT_ACCESS_WR)
        full_path = self._get_file_full_path(did, app_did, path)
        if full_path.exists():
            if full_path.is_dir():
                dir_size = get_dir_size(full_path.as_posix(), 0.0)
                shutil.rmtree(full_path)
                inc_vault_file_use_storage_byte(did, -dir_size)
            else:
                file_size = os.path.getsize(full_path.as_posix())
                full_path.unlink()
                inc_vault_file_use_storage_byte(did, -file_size)

    def move_file(self, src_path, dst_path):
        return self._move_file(src_path, dst_path)

    def copy_file(self, src_path, dst_path):
        return self._move_file(src_path, dst_path, True)

    def _move_file(self, src_path, dst_path, is_copy=False):
        did, app_did = check_auth_and_vault(VAULT_ACCESS_WR)
        full_src_path = self._get_file_full_path(did, app_did, src_path)
        full_dst_path = self._get_file_full_path(did, app_did, dst_path)
        if not full_src_path.exists():
            raise BadRequestException(msg='File to moved does not exist.')
        if full_dst_path:
            raise BadRequestException(msg='Destination file exists.')
        if not is_copy:
            shutil.move(full_src_path.as_posix(), full_dst_path.as_posix())
        else:
            if full_src_path.is_file():
                shutil.copy2(full_src_path.as_posix(), full_dst_path.as_posix())
                file_size = os.path.getsize(full_dst_path.as_posix())
                inc_vault_file_use_storage_byte(did, file_size)
            else:
                shutil.copytree(full_src_path.as_posix(), full_dst_path.as_posix())
                dir_size = get_dir_size(full_dst_path.as_posix(), 0.0)
                inc_vault_file_use_storage_byte(did, dir_size)
        return {
            'name': dst_path
        }

    def list_children(self, path):
        did, app_did = check_auth_and_vault(VAULT_ACCESS_WR)
        full_path = self._get_file_full_path(did, app_did, path)
        if not full_path.exists() or not full_path.is_dir():
            raise BadRequestException(msg='Folder does not exist.')
        files = os.listdir(full_path.as_posix())
        return list(map(lambda f: self._get_file_info(full_path, f), files))

    def _get_file_info(self, full_dir_path, file_meta):
        info = {
            'name': file_meta,
            'is_file': (full_dir_path / file_meta).is_file()
        }
        if info['is_file']:
            info['size'] = file_meta.stat.st_size
        return file_meta

    def get_properties(self, path):
        did, app_did = check_auth_and_vault(VAULT_ACCESS_WR)
        full_path = self._get_file_full_path(did, app_did, path)
        if not full_path.exists():
            raise BadRequestException(msg='File path does not exist.')

        stat = full_path.stat()
        return {
            'name': path,
            'is_file': full_path.is_file(),
            'size': stat.st_size,
            'created': stat.st_mtime,
            'updated': stat.st_birthtime
        }

    def get_hash(self, path):
        did, app_did = check_auth_and_vault(VAULT_ACCESS_WR)
        data, err = query_hash(did, app_did, path)
        if err:
            raise BadRequestException(f'Failed getting file hash code: {str(err)}')
        return {
            'name': path,
            'algorithm': 'SHA256',
            'hash': data['SHA256']
        }
