from flask import request, Response

from hive.util.auth import did_auth
from hive.util.error_code import UNAUTHORIZED, SUCCESS
from hive.util.server_response import ServerResponse
from hive.main.interceptor import post_json_param_pre_proc, pre_proc, get_pre_proc
from hive.util.constants import VAULT_ACCESS_R, VAULT_ACCESS_WR, VAULT_ACCESS_DEL
from hive.util.payment.vault_service_manage import can_access_vault
from src.modules.files.collection_file_metadata import CollectionFileMetadata
from src.modules.files.files_service import FilesService
from hive.util.v2_adapter import v2_wrapper


class HiveFile:
    def __init__(self, app=None):
        self.app = app
        self.response = ServerResponse("HiveFile")
        self.files_service = FilesService()

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

        _, resp_err = v2_wrapper(self.files_service.v1_move_copy_file)(
            did, app_id, content.get('src_path'), content.get('dst_path'), is_copy=is_copy
        )
        if resp_err:
            return resp_err

        return self.response.response_ok()

    def upload_file(self, file_name):
        did, app_id, response = pre_proc(self.response, access_vault=VAULT_ACCESS_WR)
        if response is not None:
            return response

        _, resp_err = v2_wrapper(self.files_service.v1_upload_file)(did, app_id, file_name)
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

        data, resp_err = v2_wrapper(self.files_service.v1_download_file)(did, app_id, request.args.get('path'))
        if resp_err:
            return resp_err

        return data

    def get_property(self):
        did, app_id, content, response = get_pre_proc(self.response, "path", access_vault=VAULT_ACCESS_R)
        if response is not None:
            return response

        metadata, resp_err = v2_wrapper(self.files_service.v1_get_file_metadata)(did, app_id, content['path'])
        if resp_err:
            return resp_err
        data = HiveFile.get_info_by_metadata(metadata)

        return self.response.response_ok(data)

    @staticmethod
    def get_info_by_metadata(metadata):
        return {
            "type": "file" if metadata[CollectionFileMetadata.IS_FILE] else "folder",
            "name": metadata[CollectionFileMetadata.PATH],
            "size": metadata[CollectionFileMetadata.SIZE],
            "last_modify": metadata['modified'],
        }

    def list_files(self):
        did, app_id = did_auth()
        if (did is None) or (app_id is None):
            return self.response.response_err(UNAUTHORIZED, "auth failed")

        r, msg = can_access_vault(did, VAULT_ACCESS_R)
        if r != SUCCESS:
            return self.response.response_err(r, msg)

        docs, resp_err = v2_wrapper(self.files_service.v1_list_folder)(did, app_id, request.args.get('path'))
        if resp_err:
            return resp_err
        file_info_list = list(map(lambda d: HiveFile.get_info_by_metadata(d), docs))

        return self.response.response_ok({"file_info_list": file_info_list})

    def file_hash(self):
        did, app_id, content, response = get_pre_proc(self.response, "path", access_vault=VAULT_ACCESS_R)
        if response is not None:
            return response

        metadata, resp_err = v2_wrapper(self.files_service.v1_get_file_metadata)(did, app_id, content['path'])
        if resp_err:
            return resp_err
        data = {"SHA256": metadata[CollectionFileMetadata.SHA256]}

        return self.response.response_ok(data)

    def delete(self):
        did, app_id, content, response = post_json_param_pre_proc(self.response, "path", access_vault=VAULT_ACCESS_DEL)
        if response is not None:
            return response

        _, resp_err = v2_wrapper(self.files_service.v1_delete_file)(did, app_id, content.get('path'))
        if resp_err:
            return resp_err

        return self.response.response_ok()
