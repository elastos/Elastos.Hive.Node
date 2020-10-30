from flask import Blueprint, request, jsonify

from hive.main.hive_auth import HiveAuth
from hive.main.hive_sync import HiveSync
from hive.main.hive_manage import HiveManage

h_auth = HiveAuth()
h_sync = HiveSync()
h_manage = HiveManage()

main = Blueprint('main', __name__)


def init_app(app):
    h_auth.init_app(app)
    h_sync.init_app(app)
    h_manage.init_app(app)
    app.register_blueprint(main)


@main.route('/api/v1/echo', methods=['POST'])
def echo():
    content = request.get_json()
    return jsonify(content)


# hive version
@main.route('/api/v1/hive/version', methods=['GET'])
def get_hive_version():
    return h_manage.get_hive_version()


# hive commit hash
@main.route('/api/v1/hive/commithash', methods=['GET'])
def get_hive_commit_hash():
    return h_manage.get_hive_commit_hash()


# did auth
@main.route('/api/v1/did/sign_in', methods=['POST'])
def access_request():
    return h_auth.sign_in()


@main.route('/api/v1/did/auth', methods=['POST'])
def request_did_auth():
    return h_auth.request_did_auth()


@main.route('/api/v1/did/check_token', methods=['POST'])
def check_token():
    return h_auth.check_token()


@main.route('/api/v1/did/<did_base58>/<app_id_base58>/callback', methods=['POST'])
def did_auth_callback(did_base58, app_id_base58):
    return h_auth.did_auth_callback(did_base58, app_id_base58)


# file synchronization
@main.route('/api/v1/sync/setup/google_drive', methods=['POST'])
def setup_syn_google_drive():
    return h_sync.setup_google_drive_rclone()
