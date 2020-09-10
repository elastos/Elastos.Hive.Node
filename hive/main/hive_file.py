import hashlib
import logging
import os
import urllib.parse
from datetime import datetime
from pathlib import Path
import shutil

from flask import request, Response

from hive.main.hive_sync import HiveSync
from hive.util.auth import did_auth
from hive.util.common import did_tail_part
from hive.settings import VAULTS_BASE_DIR
from hive.util.flask_rangerequest import RangeRequest
from hive.util.server_response import response_err, response_ok
from hive.main.interceptor import post_json_param_pre_proc, pre_proc, get_pre_proc


class HiveFile:
    def __init__(self, app=None):
        self.app = app

    def init_app(self, app):
        self.app = app
        self.app.config['UPLOAD_FOLDER'] = "./temp_file"
        self.app.config['MAX_CONTENT_PATH'] = 10000000

    def get_save_files_path(self, did, app_id):
        path = Path(VAULTS_BASE_DIR)
        if path.is_absolute():
            path = path / did_tail_part(did) / app_id / "files"
        else:
            path = path.resolve() / did_tail_part(did) / app_id / "files"
        return path.resolve()

    def create_full_path_dir(self, path):
        try:
            path.mkdir(exist_ok=True, parents=True)
        except Exception as e:
            logging.debug(f"Exception in create_full_path: {e}")
            return False
        return True

    def filter_path_root(self, name):
        if name[0] == "/":
            return name[1:]
        else:
            return name

    def move(self, is_copy):
        did, app_id, content, response = post_json_param_pre_proc("src_path", "dst_path")
        if response is not None:
            return response

        src_name = content.get('src_path')
        src_name = self.filter_path_root(src_name)

        dst_name = content.get('dst_path')
        dst_name = self.filter_path_root(dst_name)

        path = self.get_save_files_path(did, app_id)
        src_full_path_name = (path / src_name).resolve()
        dst_full_path_name = (path / dst_name).resolve()

        if not src_full_path_name.exists():
            return response_err(404, "src_name not exists")

        if dst_full_path_name.exists() and dst_full_path_name.is_file():
            return response_err(409, "dst_name file exists")

        dst_parent_folder = dst_full_path_name.parent
        if not dst_parent_folder.exists():
            if not self.create_full_path_dir(dst_parent_folder):
                return response_err(500, "make dst parent path dir error")
        try:
            if is_copy:
                if src_full_path_name.is_file():
                    shutil.copy2(src_full_path_name.as_posix(), dst_full_path_name.as_posix())
                else:
                    shutil.copytree(src_full_path_name.as_posix(), dst_full_path_name.as_posix())
            else:
                shutil.move(src_full_path_name.as_posix(), dst_full_path_name.as_posix())
        except Exception as e:
            return response_err(500, "Exception:" + str(e))

        return response_ok()

    def upload_file(self, file_name):
        did, app_id, response = pre_proc()
        if response is not None:
            return response

        path = self.get_save_files_path(did, app_id)
        full_path_name = (path / file_name).resolve()

        if not self.create_full_path_dir(full_path_name.parent):
            return response_err(500, "make path dir error")

        if not full_path_name.exists():
            full_path_name.touch(exist_ok=True)

        if full_path_name.is_dir():
            return response_err(404, "file name is a directory")
        try:
            with open(full_path_name, "bw") as f:
                chunk_size = 4096
                while True:
                    chunk = request.stream.read(chunk_size)
                    if len(chunk) == 0:
                        break
                    f.write(chunk)
        except Exception as e:
            return response_err(500, "Exception:"+str(e))

        return response_ok()

    def download_file(self):
        resp = Response()
        did, app_id = did_auth()
        if (did is None) or (app_id is None):
            resp.status_code = 401
            return resp

        filename = request.args.get('path')
        if filename is None:
            resp.status_code = 400
            return resp
        filename = self.filter_path_root(filename)

        path = self.get_save_files_path(did, app_id)
        file_full_name = (path / filename).resolve()

        if not file_full_name.exists():
            resp.status_code = 404
            return resp

        if not file_full_name.is_file():
            resp.status_code = 403
            return resp

        size = file_full_name.stat().st_size
        with open(file_full_name, 'rb') as f:
            etag = RangeRequest.make_etag(f)
        last_modified = datetime.utcnow()

        return RangeRequest(open(file_full_name, 'rb'),
                            etag=etag,
                            last_modified=last_modified,
                            size=size).make_response()

    def get_property(self):
        did, app_id, content, response = get_pre_proc("path")
        if response is not None:
            return response

        name = content['path']
        name = self.filter_path_root(name)

        path = self.get_save_files_path(did, app_id)
        full_path_name = (path / name).resolve()

        if not full_path_name.exists():
            return response_err(404, "file not exists")

        stat_info = full_path_name.stat()

        data = {
            "type": "file" if full_path_name.is_file() else "folder",
            "name": name,
            "size": stat_info.st_size,
            "last_modify": stat_info.st_mtime,
        }

        return response_ok(data)

    def list_files(self):
        did, app_id = did_auth()
        if (did is None) or (app_id is None):
            return response_err(401, "auth failed")

        path = self.get_save_files_path(did, app_id)

        name = request.args.get('path')
        if name is None:
            full_path_name = path
        else:
            name = self.filter_path_root(name)
            full_path_name = (path / name).resolve()

        if not (full_path_name.exists() and full_path_name.is_dir()):
            return response_err(404, "folder not exists")

        try:
            files = os.listdir(full_path_name.as_posix())
        except Exception as e:
            return response_ok({"files": []})

        file_info_list = list()
        for file in files:
            full_file = full_path_name / file
            stat_info = full_file.stat()
            file_info = {
                "type": "file" if full_file.is_file() else "folder",
                "file": file,
                "size": stat_info.st_size,
                "last_modify": stat_info.st_mtime,
            }
            file_info_list.append(file_info)

        return response_ok({"file_info_list": file_info_list})

    def file_hash(self):
        did, app_id, content, response = get_pre_proc("path")
        if response is not None:
            return response

        name = content['path']

        name = self.filter_path_root(name)

        path = self.get_save_files_path(did, app_id)
        full_path_name = (path / name).resolve()

        if not full_path_name.exists() or (not full_path_name.is_file()):
            return response_err(404, "file not exists")

        buf_size = 65536  # lets read stuff in 64kb chunks!
        sha = hashlib.sha256()
        with full_path_name.open('rb') as f:
            while True:
                data = f.read(buf_size)
                if not data:
                    break
                sha.update(data)
        data = {"SHA256": sha.hexdigest()}
        return response_ok(data)

    def delete(self):
        did, app_id, content, response = post_json_param_pre_proc("path")
        if response is not None:
            return response

        filename = content.get('path')
        filename = self.filter_path_root(filename)

        path = self.get_save_files_path(did, app_id)
        file_full_name = (path / filename).resolve()
        if file_full_name.exists():
            if file_full_name.is_dir():
                shutil.rmtree(file_full_name)
            else:
                file_full_name.unlink()

        return response_ok()
