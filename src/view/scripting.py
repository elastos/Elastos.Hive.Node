# -*- coding: utf-8 -*-

"""
The view of scripting module.
"""
from flask import Blueprint

from src.modules.scripting.scripting import Scripting

blueprint = Blueprint('scripting', __name__)
scripting = Scripting()


def init_app(app):
    """ This will be called by application initializer. """
    app.register_blueprint(blueprint)


@blueprint.route('/api/v2/vault/scripting/<script_name>', methods=['PUT'])
def register_script(script_name):
    return scripting.set_script(script_name)


@blueprint.route('/api/v2/vault/scripting/<script_name>', methods=['DELETE'])
def delete_script(script_name):
    return scripting.delete_script(script_name)


@blueprint.route('/api/v2/vault/scripting/<script_name>', methods=['PATCH'])
def call_script(script_name):
    return scripting.run_script(script_name)


@blueprint.route('/api/v2/vault/scripting/<script_name>/<target_did>@<target_app_did>/<params>', methods=['GET'])
def call_script_url(script_name, target_did, target_app_did, params):
    return scripting.run_script_url(script_name, target_did, target_app_did, params)


@blueprint.route('/api/v2/vault/scripting/stream/{transaction_id}', methods=['PUT'])
def upload_file(transaction_id):
    return scripting.upload_file(transaction_id)


@blueprint.route('/api/v2/vault/scripting/stream/{transaction_id}', methods=['GET'])
def download_file(transaction_id):
    return scripting.download_file(transaction_id)
