import os

from flask import request, send_from_directory, make_response

from hive.util.auth import did_auth
from hive.util.constants import DID_FILE_DIR, did_tail_part
from hive.util.server_response import response_err, response_ok


class HiveFile:
    def __init__(self, app=None):
        self.app = app

    def init_app(self, app):
        self.app = app
        self.app.config['UPLOAD_FOLDER'] = "./temp_file"
        self.app.config['MAX_CONTENT_PATH'] = 10000000

    def get_file_path(did):
        if not os.path.isabs(DID_FILE_DIR):
            directory = os.getcwd()
            path = directory + "/" + DID_FILE_DIR + "/" + did_tail_part(did) + "/"
        else:
            path = DID_FILE_DIR + "/" + did_tail_part(did) + "/"
        return path

    def upload_file(self):
        did = did_auth()
        if did is None:
            return response_err(401, "auth failed")

        f = request.files['file']
        if f is None:
            return response_err(400, "file is null")

        path = self.get_file_path(did)

        try:
            os.makedirs(path, exist_ok=True)
            f.save(path + f.filename.strip('"'))
        except Exception as e:
            print("Exception in upload_file:" + e)
            return response_err(500, "Save file error")

        return response_ok()

    def delete_file(self):
        did = did_auth()
        if did is None:
            return response_err(401, "auth failed")

        content = request.get_json(force=True, silent=True)
        if content is None:
            return response_err(400, "parameter is not application/json")
        filename = content.get('file_name', None)

        path = self.get_file_path(did)
        fullname = os.path.join(path, filename)
        if os.path.exists(fullname) and os.path.isfile(fullname):
            os.remove(fullname)
            return response_ok()
        else:
            return response_err(404, "File not found")

    def download_file(self):
        did = did_auth()
        if did is None:
            return response_err(401, "auth failed")

        filename = request.args.get('filename')
        if filename is None:
            return response_err(401, "file name is null")

        path = self.get_file_path(did)

        if not os.path.exists(path + filename.encode('utf-8').decode('utf-8')):
            return response_err(404, "file not found")

        response = make_response(
            send_from_directory(path, filename.encode('utf-8').decode('utf-8'), as_attachment=True))
        response.headers["Content-Disposition"] = "attachment; filename={}".format(filename.encode().decode('latin-1'))
        return response

    def get_file_info(self):
        did = did_auth()
        if did is None:
            return response_err(401, "auth failed")

        filename = request.args.get('filename')
        if filename is None:
            return response_err(401, "file name is null")

        path = self.get_file_path(did)

        file_full_name = path + filename.encode('utf-8').decode('utf-8')
        if not os.path.exists(file_full_name):
            return response_err(404, "file not found")

        size = os.path.getsize(file_full_name)

        return response_ok({"file": filename, "size": size})

    def list_files(self):
        did = did_auth()
        if did is None:
            return response_err(401, "auth failed")
        path = self.get_file_path(did)
        try:
            files = os.listdir(path)
        except Exception as e:
            return response_ok({"files": []})

        names = [name for name in files
                 if os.path.isfile(os.path.join(path, name))]
        return response_ok({"files": names})
