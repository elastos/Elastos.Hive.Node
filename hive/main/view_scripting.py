import json

from flask import Blueprint, request

from hive.main.hive_scripting import HiveScripting, HiveScriptingV2

h_scripting = HiveScripting()
h_scripting_v2 = HiveScriptingV2()

hive_scripting = Blueprint('hive_scripting', __name__)


def init_app(app):
    h_scripting.init_app(app)
    app.register_blueprint(hive_scripting)


@hive_scripting.route('/api/v1/scripting/set_script', methods=['POST'])
def set_script():
    return h_scripting.set_script()


@hive_scripting.route('/api/v1/scripting/run_script', methods=['POST'])
def run_script():
    return h_scripting.run_script()


@hive_scripting.route('/api/v1/scripting/run_script_url/<target_did>@<target_app_did>/<script_name>', methods=['GET'])
def run_script_url(target_did, target_app_did, script_name):
    # Get parameters
    try:
        params = request.args.get("params")
        params = json.loads(params)
    except:
        params = {}
    return h_scripting.run_script_url(target_did, target_app_did, script_name, params)


@hive_scripting.route('/api/v1/scripting/run_script_upload/<path:transaction_id>', methods=['POST'])
def run_script_upload(transaction_id):
    return h_scripting.run_script_upload(transaction_id)


@hive_scripting.route('/api/v1/scripting/run_script_download/<path:transaction_id>', methods=['POST'])
def run_script_download(transaction_id):
    return h_scripting.run_script_download(transaction_id)


@hive_scripting.route('/api/v2/vault/scripting/<script_name>', methods=['PUT'])
def register_script(script_name):
    return h_scripting_v2.set_script(script_name)


@hive_scripting.route('/api/v2/vault/scripting/<script_name>', methods=['DELETE'])
def delete_script(script_name):
    return h_scripting_v2.delete_script(script_name)


@hive_scripting.route('/api/v2/vault/scripting/<script_name>', methods=['PATCH'])
def call_script(script_name):
    return h_scripting_v2.run_script(script_name)


@hive_scripting.route('/api/v2/vault/scripting/<script_name>/<target_did>@<target_app_did>/<params>', methods=['GET'])
def call_script_url(script_name, target_did, target_app_did, params):
    return h_scripting_v2.run_script_url(script_name, target_did, target_app_did, params)


@hive_scripting.route('/api/v2/vault/scripting/stream/{transaction_id}', methods=['PUT'])
def upload_file(transaction_id):
    return h_scripting_v2.upload_file(transaction_id)


@hive_scripting.route('/api/v2/vault/scripting/stream/{transaction_id}', methods=['GET'])
def download_file(transaction_id):
    return h_scripting_v2.download_file(transaction_id)
