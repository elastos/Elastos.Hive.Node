import os

from flask import request, send_from_directory, make_response

from hive.util.auth import did_auth
from hive.util.constants import DID_FILE_DIR, did_tail_part, FILE_INFO_FILE_NAME, FILE_INFO_FILE_SIZE
from hive.util.file_info import add_file_info, update_file_info, get_file_info_by_id, remove_file_info, \
    update_file_size, get_file_info
from hive.util.server_response import response_err, response_ok


class HiveFile:
    def __init__(self, app=None):
        self.app = app

    def init_app(self, app):
        self.app = app
        self.app.config['UPLOAD_FOLDER'] = "./temp_file"
        self.app.config['MAX_CONTENT_PATH'] = 10000000

    def get_file_path(self, did, app_id):
        if not os.path.isabs(DID_FILE_DIR):
            directory = os.getcwd()
            path = directory + "/" + DID_FILE_DIR + "/" + did_tail_part(did) + "/" + app_id + "/"
        else:
            path = DID_FILE_DIR + "/" + did_tail_part(did) + "/" + app_id + "/"
        return path

    def create_full_path(self, path):
        try:
            os.makedirs(path, exist_ok=True)
        except Exception as e:
            print("Exception in create_full_path:" + e)
            return False
        return True;

    def create_upload_file(self):
        did, app_id = did_auth()
        if (did is None) or (app_id is None):
            return response_err(401, "auth failed")
        content = request.get_json(force=True, silent=True)
        if content is None:
            return response_err(400, "parameter is not application/json")
        filename = content.get('file_name', None)
        del content['file_name']

        file_id = ""
        info = get_file_info(did, app_id, filename)
        if (info is not None) and (FILE_INFO_FILE_SIZE in info):
            return response_err(400, "file exist")
        else:
            if info:
                file_id = info["_id"]
            else:
                r = add_file_info(did, app_id, filename, content)
                file_id = r.inserted_id

        data = {"upload_file_url": "/api/v1/%s/upload" % file_id}

        return response_ok(data)

    def set_file_property(self):
        did, app_id = did_auth()
        if (did is None) or (app_id is None):
            return response_err(401, "auth failed")
        content = request.get_json(force=True, silent=True)
        if content is None:
            return response_err(400, "parameter is not application/json")
        filename = content.get('file_name', None)
        del content['file_name']
        update_file_info(did, app_id, filename, content)
        return response_ok()

    def get_file_property(self):
        did, app_id = did_auth()
        if (did is None) or (app_id is None):
            return response_err(401, "auth failed")

        filename = request.args.get('filename')
        if filename is None:
            return response_err(401, "file name is null")

        info = get_file_info(did, app_id, filename)
        if info is None:
            return response_err(404, "File not found")

        info["upload_file_url"] = "/api/v1/%s/upload" % info["_id"]

        del info["_id"]
        return response_ok(info)

    def upload_file_callback(self, file_id):
        did, app_id = did_auth()
        if (did is None) or (app_id is None):
            return response_err(401, "auth failed")

        info = get_file_info_by_id(file_id)
        if info is None:
            return response_err(404, "file not found")

        path = self.get_file_path(did, app_id)
        file_full_name = path + info[FILE_INFO_FILE_NAME]
        if not self.create_full_path(path):
            return response_err(500, "make dir error")

        with open(file_full_name, "bw") as f:
            chunk_size = 4096
            while True:
                chunk = request.stream.read(chunk_size)
                if len(chunk) == 0:
                    break
                f.write(chunk)

        size = os.path.getsize(file_full_name)

        r = update_file_size(did, app_id, info[FILE_INFO_FILE_NAME], {FILE_INFO_FILE_SIZE: size})
        return response_ok()


    def upload_file_old(self):
        did, app_id = did_auth()
        if (did is None) or (app_id is None):
            return response_err(401, "auth failed")
        f = request.files['file']
        if f is None:
            return response_err(400, "file is null")

        path = self.get_file_path(did, app_id)
        file_full_name = path + f.filename.strip('"')
        if not self.create_full_path(path):
            return response_err(500, "make dir error")

        try:
            f.save(file_full_name)
        except Exception as e:
            print("Exception in upload_file:" + e)
            return response_err(500, "Save file error")

        size = os.path.getsize(file_full_name)

        r = add_file_info(did, app_id, f.filename.strip('"'), {FILE_INFO_FILE_SIZE: size})
        return response_ok()

    def delete_file(self):
        did, app_id = did_auth()
        if (did is None) or (app_id is None):
            return response_err(401, "auth failed")

        content = request.get_json(force=True, silent=True)
        if content is None:
            return response_err(400, "parameter is not application/json")
        filename = content.get('file_name', None)

        path = self.get_file_path(did, app_id)
        fullname = os.path.join(path, filename)
        if os.path.exists(fullname) and os.path.isfile(fullname):
            os.remove(fullname)
            remove_file_info(did, app_id, filename)
            return response_ok()
        else:
            return response_err(404, "File not found")

    def download_file(self):
        did, app_id = did_auth()
        if (did is None) or (app_id is None):
            return response_err(401, "auth failed")

        filename = request.args.get('filename')
        if filename is None:
            return response_err(401, "file name is null")

        path = self.get_file_path(did, app_id)

        if not os.path.exists(path + filename.encode('utf-8').decode('utf-8')):
            return response_err(404, "file not found")

        response = make_response(
            send_from_directory(path, filename.encode('utf-8').decode('utf-8'), as_attachment=True))
        response.headers["Content-Disposition"] = "attachment; filename={}".format(filename.encode().decode('latin-1'))
        return response

    def list_files(self):
        did, app_id = did_auth()
        if (did is None) or (app_id is None):
            return response_err(401, "auth failed")
        path = self.get_file_path(did, app_id)
        try:
            files = os.listdir(path)
        except Exception as e:
            return response_ok({"files": []})

        names = [name for name in files
                 if os.path.isfile(os.path.join(path, name)) or os.path.isdir(os.path.join(path, name))]
        return response_ok({"files": names})
