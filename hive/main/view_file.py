from flask import Blueprint

from hive.main.hive_file import HiveFile

hive_file = Blueprint('hive_file', __name__)
h_file: HiveFile = None


def init_app(app):
    global h_file
    h_file = HiveFile()
    h_file.init_app(app)
    app.register_blueprint(hive_file)


@hive_file.route('/api/v1/files/upload/<path:file_name>', methods=['POST'])
def upload_file(file_name):
    return h_file.upload_file(file_name)


@hive_file.route('/api/v1/files/download', methods=['GET'])
def download_file():
    return h_file.download_file()


@hive_file.route('/api/v1/files/delete', methods=['POST'])
def remove():
    return h_file.delete()


@hive_file.route('/api/v1/files/move', methods=['POST'])
def move_files():
    return h_file.move(is_copy=False)


@hive_file.route('/api/v1/files/copy', methods=['POST'])
def copy_files():
    return h_file.move(is_copy=True)


@hive_file.route('/api/v1/files/properties', methods=['GET'])
def file_info():
    return h_file.get_property()


@hive_file.route('/api/v1/files/list/folder', methods=['GET'])
def list_files():
    return h_file.list_files()


@hive_file.route('/api/v1/files/file/hash', methods=['GET'])
def get_file_hash():
    return h_file.file_hash()

