import logging
import os
import shutil

from flask import request, Response

from hive.util.auth import did_auth
from hive.util.common import create_full_path_dir, gene_temp_file_name
from hive.util.did_file_info import get_save_files_path, filter_path_root, query_download, \
    query_properties, query_hash, query_upload_get_filepath, get_dir_size
from hive.util.error_code import INTERNAL_SERVER_ERROR, UNAUTHORIZED, NOT_FOUND, METHOD_NOT_ALLOWED, SUCCESS, FORBIDDEN, \
    BAD_REQUEST
from hive.util.server_response import ServerResponse
from hive.main.interceptor import post_json_param_pre_proc, pre_proc, get_pre_proc
from hive.util.constants import VAULT_ACCESS_R, VAULT_ACCESS_WR, VAULT_ACCESS_DEL, CHUNK_SIZE
from hive.util.payment.vault_service_manage import can_access_vault, inc_vault_file_use_storage_byte
from src.modules.ipfs.ipfs_files import IpfsFiles
from src.utils.consts import COL_IPFS_FILES_IS_FILE, COL_IPFS_FILES_PATH, SIZE, COL_IPFS_FILES_SHA256
from hive.util.v2_adapter import v2_wrapper


class HiveFile:
    def __init__(self, app=None):
        self.app = app
        self.response = ServerResponse("HiveFile")
        self.ipfs_files = IpfsFiles()

    def init_app(self, app):
        self.app = app
        self.app.config['UPLOAD_FOLDER'] = "./temp_file"
        self.app.config['MAX_CONTENT_PATH'] = 10000000
        self.app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

    def move(self, is_copy):
        did, app_id, content, response = post_json_param_pre_proc(self.response, "src_path", "dst_path",
                                                                  access_vault=VAULT_ACCESS_WR)
        if response is not None:
            return response

        _, resp_err = v2_wrapper(self.ipfs_files.move_copy_file)(
            did, app_id, content.get('src_path'), content.get('dst_path'), is_copy=is_copy
        )
        if resp_err:
            return resp_err

        return self.response.response_ok()

    def upload_file(self, file_name):
        did, app_id, response = pre_proc(self.response, access_vault=VAULT_ACCESS_WR)
        if response is not None:
            return response

        _, resp_err = v2_wrapper(self.ipfs_files.upload_file_with_path)(did, app_id, file_name)
        if resp_err:
            return resp_err

        return self.response.response_ok()

    def download_file(self):
        resp = Response()
        did, app_id = did_auth()
        if (did is None) or (app_id is None):
            resp.status_code = UNAUTHORIZED
            return resp
        r, msg = can_access_vault(did, VAULT_ACCESS_R)
        if r != SUCCESS:
            resp.status_code = r
            return resp

        data, resp_err = v2_wrapper(self.ipfs_files.download_file_with_path)(did, app_id, request.args.get('path'))
        if resp_err:
            return resp_err

        return data

    def get_property(self):
        did, app_id, content, response = get_pre_proc(self.response, "path", access_vault=VAULT_ACCESS_R)
        if response is not None:
            return response

        metadata, resp_err = v2_wrapper(self.ipfs_files.get_file_metadata)(did, app_id, content['path'])
        if resp_err:
            return resp_err
        data = HiveFile.get_info_by_metadata(metadata)

        return self.response.response_ok(data)

    @staticmethod
    def get_info_by_metadata(metadata):
        return {
            "type": "file" if metadata[COL_IPFS_FILES_IS_FILE] else "folder",
            "name": metadata[COL_IPFS_FILES_PATH],
            "size": metadata[SIZE],
            "last_modify": metadata['modified'],
        }

    def list_files(self):
        did, app_id = did_auth()
        if (did is None) or (app_id is None):
            return self.response.response_err(UNAUTHORIZED, "auth failed")

        r, msg = can_access_vault(did, VAULT_ACCESS_R)
        if r != SUCCESS:
            return self.response.response_err(r, msg)

        docs, resp_err = v2_wrapper(self.ipfs_files.list_folder_with_path)(did, app_id, request.args.get('path'))
        if resp_err:
            return resp_err
        file_info_list = list(map(lambda d: HiveFile.get_info_by_metadata(d), docs))

        return self.response.response_ok({"file_info_list": file_info_list})

    def file_hash(self):
        did, app_id, content, response = get_pre_proc(self.response, "path", access_vault=VAULT_ACCESS_R)
        if response is not None:
            return response

        metadata, resp_err = v2_wrapper(self.ipfs_files.get_file_metadata)(did, app_id, content['path'])
        if resp_err:
            return resp_err
        data = {"SHA256": metadata[COL_IPFS_FILES_SHA256]}

        return self.response.response_ok(data)

    def delete(self):
        did, app_id, content, response = post_json_param_pre_proc(self.response, "path", access_vault=VAULT_ACCESS_DEL)
        if response is not None:
            return response

        _, resp_err = v2_wrapper(self.ipfs_files.delete_file_with_path)(did, app_id, content.get('path'))
        if resp_err:
            return resp_err

        return self.response.response_ok()
