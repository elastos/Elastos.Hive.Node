from flask import Blueprint, request, jsonify

from hive.main.hive_file import HiveFile
from hive.main.hive_auth import HiveAuth
from hive.main.hive_sync import HiveSync

h_file = HiveFile()
h_auth = HiveAuth()
h_sync = HiveSync()


main = Blueprint('main', __name__)


def init_app(app):
    h_auth.init_app(app)
    h_file.init_app(app)
    h_sync.init_app(app)
    app.register_blueprint(main)


@main.route('/api/v1/echo', methods=['POST'])
def echo():
    # get_json(force=False, silent=False, cache=True)
    # 获取json失败会直接返回
    content = request.get_json()
    return jsonify(content)


# did register
@main.route('/api/v1/did/auth', methods=['POST'])
def request_did_auth():
    return h_auth.request_did_auth()


@main.route('/api/v1/did/<did_base58>/<app_id_base58>/callback', methods=['POST'])
def did_auth_callback(did_base58, app_id_base58):
    return h_auth.did_auth_callback(did_base58, app_id_base58)


# file create and get
@main.route('/api/v1/files/creator/folder', methods=['POST'])
def create_folder():
    return h_file.create(is_file=False)


@main.route('/api/v1/files/creator/file', methods=['POST'])
def create_file():
    return h_file.create(is_file=True)


@main.route('/api/v1/files/uploader/<path:file_name>', methods=['POST'])
def upload_file(file_name):
    return h_file.upload_file(file_name)


@main.route('/api/v1/files/downloader', methods=['GET'])
def download_file():
    return h_file.download_file()


@main.route('/api/v1/files/deleter/file', methods=['POST'])
def remove_file():
    return h_file.delete()


@main.route('/api/v1/files/deleter/folder', methods=['POST'])
def remove_folder():
    return h_file.delete()


@main.route('/api/v1/files/mover', methods=['POST'])
def move_files():
    return h_file.move(is_copy=False)


@main.route('/api/v1/files/copier', methods=['POST'])
def copy_files():
    return h_file.move(is_copy=True)


@main.route('/api/v1/files/properties', methods=['GET'])
def file_info():
    return h_file.get_property()


@main.route('/api/v1/files/list/folder', methods=['GET'])
def list_files():
    return h_file.list_files()


@main.route('/api/v1/files/file/hash', methods=['GET'])
def get_file_hash():
    return h_file.file_hash()


# file synchronization
@main.route('/api/v1/sync/setup/google_drive', methods=['POST'])
def setup_syn_google_drive():
    return h_sync.setup_google_drive_rclone()
