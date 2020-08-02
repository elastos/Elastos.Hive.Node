import hashlib
import os
import urllib.parse
from datetime import datetime
from pathlib import Path
import shutil

from flask import request, Response

from hive.main.hive_sync import HiveSync
from hive.util.auth import did_auth
from hive.util.common import did_tail_part
from hive.settings import DID_BASE_DIR
from hive.util.flask_rangerequest import RangeRequest
from hive.util.server_response import response_err, response_ok


class HiveFile:
    def __init__(self, app=None):
        self.app = app

    def init_app(self, app):
        self.app = app
        self.app.config['UPLOAD_FOLDER'] = "./temp_file"
        self.app.config['MAX_CONTENT_PATH'] = 10000000

    def get_save_files_path(self, did, app_id):
        path = Path(DID_BASE_DIR)
        if path.is_absolute():
            path = path / did_tail_part(did) / app_id / "files"
        else:
            path = path.resolve() / did_tail_part(did) / app_id / "files"
        return path.resolve()

    def create_full_path_dir(self, path):
        try:
            path.mkdir(exist_ok=True, parents=True)
        except Exception as e:
            print("Exception in create_full_path:" + e)
            return False
        return True

    def filter_path_root(self, name):
        if name[0] == "/":
            return name[1:]
        else:
            return name

    def create(self, is_file):
        did, app_id = did_auth()
        if (did is None) or (app_id is None):
            return response_err(401, "auth failed")

        if not HiveSync.is_app_sync_prepared(did, app_id):
            return response_err(406, "drive is not prepared")

        content = request.get_json(force=True, silent=True)
        if content is None:
            return response_err(400, "parameter is not application/json")

        name = content.get('name', None)
        if name is None:
            return response_err(404, "name is null")
        name = self.filter_path_root(name)

        path = self.get_save_files_path(did, app_id)
        full_path_name = (path / name).resolve()
        if is_file:
            if not self.create_full_path_dir(full_path_name.parent):
                return response_err(500, "make path dir error")
            if not full_path_name.exists():
                full_path_name.touch(exist_ok=True)
            data = {"upload_file_url": "/api/v1/files/uploader/%s" % urllib.parse.quote_plus(name)}
            return response_ok(data)
        else:
            if not full_path_name.exists():
                if not self.create_full_path_dir(full_path_name):
                    return response_err(500, "make folder error")
            return response_ok()

    def move(self, is_copy):
        did, app_id = did_auth()
        if (did is None) or (app_id is None):
            return response_err(401, "auth failed")

        if not HiveSync.is_app_sync_prepared(did, app_id):
            return response_err(406, "drive is not prepared")

        content = request.get_json(force=True, silent=True)
        if content is None:
            return response_err(400, "parameter is not application/json")

        src_name = content.get('src_name', None)
        if src_name is None:
            return response_err(404, "src_name is null")
        src_name = self.filter_path_root(src_name)

        dst_name = content.get('dst_name', None)
        if dst_name is None:
            return response_err(404, "dst_name is null")
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
        did, app_id = did_auth()
        if (did is None) or (app_id is None):
            return response_err(401, "auth failed")

        if not HiveSync.is_app_sync_prepared(did, app_id):
            return response_err(406, "drive is not prepared")

        path = self.get_save_files_path(did, app_id)
        file_full_name = (path / urllib.parse.unquote_plus(file_name)).resolve()

        if not (file_full_name.exists() and file_full_name.is_file()):
            return response_err(404, "file not create first")

        with open(file_full_name, "bw") as f:
            chunk_size = 4096
            while True:
                chunk = request.stream.read(chunk_size)
                if len(chunk) == 0:
                    break
                f.write(chunk)

        return response_ok()

    def download_file(self):
        resp = Response()
        did, app_id = did_auth()
        if (did is None) or (app_id is None):
            resp.status_code = 401
            return resp

        if not HiveSync.is_app_sync_prepared(did, app_id):
            return response_err(406, "drive is not prepared")

        filename = request.args.get('name')
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
        did, app_id = did_auth()
        if (did is None) or (app_id is None):
            return response_err(401, "auth failed")

        if not HiveSync.is_app_sync_prepared(did, app_id):
            return response_err(406, "drive is not prepared")

        name = request.args.get('name')
        if name is None:
            return response_err(404, "name is null")

        name = self.filter_path_root(name)

        path = self.get_save_files_path(did, app_id)
        full_path_name = (path / name).resolve()

        if not full_path_name.exists():
            return response_err(404, "file not exists")

        stat_info = full_path_name.stat()
        data = {
            "st_ctime": stat_info.st_ctime,
            "st_mtime": stat_info.st_mtime,
            "st_atime": stat_info.st_atime,
            "st_size": stat_info.st_size,
        }

        return response_ok(data)

    def list_files(self):
        did, app_id = did_auth()
        if (did is None) or (app_id is None):
            return response_err(401, "auth failed")

        if not HiveSync.is_app_sync_prepared(did, app_id):
            return response_err(406, "drive is not prepared")

        path = self.get_save_files_path(did, app_id)

        name = request.args.get('name')
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

        names = list()
        for name in files:
            if (full_path_name / name).is_file():
                names.append(name)
            elif (full_path_name / name).is_dir():
                names.append(name + "/")
        return response_ok({"files": names})

    def file_hash(self):
        did, app_id = did_auth()
        if (did is None) or (app_id is None):
            return response_err(401, "auth failed")

        if not HiveSync.is_app_sync_prepared(did, app_id):
            return response_err(406, "drive is not prepared")

        name = request.args.get('name')
        if name is None:
            return response_err(404, "name is null")
        name = self.filter_path_root(name)

        path = self.get_save_files_path(did, app_id)
        full_path_name = (path / name).resolve()

        if not full_path_name.exists() or (not full_path_name.is_file()):
            return response_err(404, "file not exists")

        buf_size = 65536  # lets read stuff in 64kb chunks!
        md5 = hashlib.md5()
        with full_path_name.open() as f:
            while True:
                data = f.read(buf_size)
                if not data:
                    break
                md5.update(data.encode("utf-8"))
        data = {"MD5": md5.hexdigest()}
        return response_ok(data)

    def delete(self):
        did, app_id = did_auth()
        if (did is None) or (app_id is None):
            return response_err(401, "auth failed")

        if not HiveSync.is_app_sync_prepared(did, app_id):
            return response_err(406, "drive is not prepared")

        content = request.get_json(force=True, silent=True)
        if content is None:
            return response_err(400, "parameter is not application/json")
        filename = content.get('name', None)
        if filename is None:
            return response_err(404, "name is null")
        filename = self.filter_path_root(filename)

        path = self.get_save_files_path(did, app_id)
        file_full_name = (path / filename).resolve()
        if file_full_name.exists():
            if file_full_name.is_dir():
                shutil.rmtree(file_full_name)
            else:
                file_full_name.unlink()

        return response_ok()
