import logging
import os
import shutil

from flask import request, Response

from hive.util.auth import did_auth
from hive.util.common import create_full_path_dir
from hive.util.did_file_info import get_save_files_path, filter_path_root, query_download, \
    query_properties, query_hash, query_upload_get_filepath, get_dir_size
from hive.util.server_response import ServerResponse
from hive.main.interceptor import post_json_param_pre_proc, pre_proc, get_pre_proc
from hive.util.constants import VAULT_ACCESS_R, VAULT_ACCESS_WR
from hive.util.payment.vault_service_manage import can_access_vault, inc_vault_file_use_storage_byte


class HiveFile:
    def __init__(self, app=None):
        self.app = app
        self.response = ServerResponse("HiveFile")

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

        src_name = content.get('src_path')
        src_name = filter_path_root(src_name)

        dst_name = content.get('dst_path')
        dst_name = filter_path_root(dst_name)

        path = get_save_files_path(did, app_id)
        src_full_path_name = (path / src_name).resolve()
        dst_full_path_name = (path / dst_name).resolve()

        if not src_full_path_name.exists():
            return self.response.response_err(404, "src_name not exists")

        if dst_full_path_name.exists() and dst_full_path_name.is_file():
            return self.response.response_err(409, "dst_name file exists")

        dst_parent_folder = dst_full_path_name.parent
        if not dst_parent_folder.exists():
            if not create_full_path_dir(dst_parent_folder):
                return self.response.response_err(500, "make dst parent path dir error")
        try:
            if is_copy:
                if src_full_path_name.is_file():
                    shutil.copy2(src_full_path_name.as_posix(), dst_full_path_name.as_posix())
                    file_size = os.path.getsize(dst_full_path_name.as_posix())
                    inc_vault_file_use_storage_byte(did, file_size)
                else:
                    shutil.copytree(src_full_path_name.as_posix(), dst_full_path_name.as_posix())
                    dir_size = 0.0
                    get_dir_size(dst_full_path_name.as_posix(), dir_size)
                    inc_vault_file_use_storage_byte(did, dir_size)
            else:
                shutil.move(src_full_path_name.as_posix(), dst_full_path_name.as_posix())
        except Exception as e:
            return self.response.response_err(500, "Exception:" + str(e))

        return self.response.response_ok()

    def upload_file(self, file_name):
        did, app_id, response = pre_proc(self.response, access_vault=VAULT_ACCESS_WR)
        if response is not None:
            return response

        file_name = filter_path_root(file_name)

        full_path_name, err = query_upload_get_filepath(did, app_id, file_name)
        if err:
            return self.response.response_err(err["status_code"], err["description"])
        try:
            with open(full_path_name, "bw") as f:
                chunk_size = 4096
                while True:
                    chunk = request.stream.read(chunk_size)
                    if len(chunk) == 0:
                        break
                    f.write(chunk)
            file_size = os.path.getsize(full_path_name.as_posix())
            inc_vault_file_use_storage_byte(did, file_size)
        except Exception as e:
            return self.response.response_err(500, f"Exception: {str(e)}")

        return self.response.response_ok()

    def download_file(self):
        resp = Response()
        did, app_id = did_auth()
        if (did is None) or (app_id is None):
            resp.status_code = 401
            return resp

        if not can_access_vault(did, VAULT_ACCESS_R):
            resp.status_code = 402
            return resp

        file_name = request.args.get('path')
        data, status_code = query_download(did, app_id, file_name)
        if status_code != 200:
            resp.status_code = status_code
            return resp

        return data

    def get_property(self):
        did, app_id, content, response = get_pre_proc(self.response, "path", access_vault=VAULT_ACCESS_R)
        if response is not None:
            return response

        name = content['path']
        data, err = query_properties(did, app_id, name)
        if err:
            return self.response.response_err(err["status_code"], err["description"])

        return self.response.response_ok(data)

    def list_files(self):
        did, app_id = did_auth()
        if (did is None) or (app_id is None):
            return self.response.response_err(401, "auth failed")

        if not can_access_vault(did, VAULT_ACCESS_R):
            return self.response.response_err(401, "access vault failed")

        path = get_save_files_path(did, app_id)

        name = request.args.get('path')
        if name is None:
            full_path_name = path
        else:
            name = filter_path_root(name)
            full_path_name = (path / name).resolve()

        if not (full_path_name.exists() and full_path_name.is_dir()):
            return self.response.response_err(404, "folder not exists")

        try:
            files = os.listdir(full_path_name.as_posix())
        except Exception as e:
            return self.response.response_ok({"files": []})

        file_info_list = list()
        for file in files:
            full_file = full_path_name / file
            stat_info = full_file.stat()
            file_info = {
                "type": "file" if full_file.is_file() else "folder",
                "name": file,
                "size": stat_info.st_size,
                "last_modify": stat_info.st_mtime,
            }
            file_info_list.append(file_info)

        return self.response.response_ok({"file_info_list": file_info_list})

    def file_hash(self):
        did, app_id, content, response = get_pre_proc(self.response, "path", access_vault=VAULT_ACCESS_R)
        if response is not None:
            return response

        name = content['path']
        data, err = query_hash(did, app_id, name)
        if err:
            return self.response.response_err(err["status_code"], err["description"])

        return self.response.response_ok(data)

    def delete(self):
        did, app_id, content, response = post_json_param_pre_proc(self.response, "path", access_vault=VAULT_ACCESS_R)
        if response is not None:
            return response

        filename = content.get('path')
        filename = filter_path_root(filename)

        path = get_save_files_path(did, app_id)
        file_full_name = (path / filename).resolve()
        if file_full_name.exists():
            if file_full_name.is_dir():
                dir_size = 0.0
                get_dir_size(file_full_name.as_posix(), dir_size)
                shutil.rmtree(file_full_name)
                inc_vault_file_use_storage_byte(did, -dir_size)
            else:
                file_size = os.path.getsize(file_full_name.as_posix())
                file_full_name.unlink()
                inc_vault_file_use_storage_byte(did, -file_size)

        return self.response.response_ok()
