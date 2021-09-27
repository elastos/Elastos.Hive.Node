# -*- coding: utf-8 -*-

"""
The view of ipfs module for files and scripting.
"""
import json

from flask import Blueprint

from src.modules.scripting.scripting import Scripting

blueprint = Blueprint('ipfs-scripting', __name__)
scripting = Scripting(is_ipfs=True)


def init_app(app, hive_setting):
    """ This will be called by application initializer. """
    global scripting
    scripting = Scripting(app=app, hive_setting=hive_setting, is_ipfs=True)
    app.register_blueprint(blueprint)


@blueprint.route('/api/v2/vault/scripting/<script_name>', methods=['PATCH'])
def call_script(script_name):
    return scripting.run_script(script_name)


@blueprint.route('/api/v2/vault/scripting/<script_name>/<context_str>/<params>', methods=['GET'])
def call_script_url(script_name, context_str, params):
    target_did, target_app_did = None, None
    parts = context_str.split('@')
    if len(parts) == 2 and parts[0] and parts[1]:
        target_did, target_app_did = parts[0], parts[1]
    return scripting.run_script_url(script_name, target_did, target_app_did, json.loads(params))


@blueprint.route('/api/v2/vault/scripting/stream/<transaction_id>', methods=['PUT'])
def upload_file(transaction_id):
    return scripting.upload_file(transaction_id)


@blueprint.route('/api/v2/vault/scripting/stream/<transaction_id>', methods=['GET'])
def download_file(transaction_id):
    return scripting.download_file(transaction_id)
