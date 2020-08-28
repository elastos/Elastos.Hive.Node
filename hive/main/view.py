from flask import Blueprint, request, jsonify

from hive.main.hive_file import HiveFile
from hive.main.hive_auth import HiveAuth
from hive.main.hive_sync import HiveSync
from hive.main.hive_scripting import HiveScripting

h_auth = HiveAuth()
h_sync = HiveSync()
h_scripting = HiveScripting()


main = Blueprint('main', __name__)


def init_app(app):
    h_auth.init_app(app)
    h_sync.init_app(app)
    h_scripting.init_app(app)
    app.register_blueprint(main)


@main.route('/api/v1/echo', methods=['POST'])
def echo():
    content = request.get_json()
    return jsonify(content)


# did register
@main.route('/api/v1/did/auth', methods=['POST'])
def request_did_auth():
    return h_auth.request_did_auth()


@main.route('/api/v1/did/<did_base58>/<app_id_base58>/callback', methods=['POST'])
def did_auth_callback(did_base58, app_id_base58):
    return h_auth.did_auth_callback(did_base58, app_id_base58)


# file synchronization
@main.route('/api/v1/sync/setup/google_drive', methods=['POST'])
def setup_syn_google_drive():
    return h_sync.setup_google_drive_rclone()


# Scripting mechanism
@main.route('/api/v1/scripting/set_subcondition', methods=['POST'])
def set_subcondition():
    return h_scripting.set_subcondition()


@main.route('/api/v1/scripting/set_script', methods=['POST'])
def set_script():
    return h_scripting.set_script()


@main.route('/api/v1/scripting/run_script', methods=['POST'])
def run_script():
    return h_scripting.run_script()
