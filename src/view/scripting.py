# -*- coding: utf-8 -*-

"""
The view of scripting module.
"""
from flask import Blueprint

from src.modules.scripting.scripting import Scripting

scripting_bp = Blueprint('scripting', __name__)
scripting = Scripting()


@scripting_bp.route('/api/v2/vault/scripting/<script_name>', methods=['PUT'])
def register_script(script_name):
    return scripting.set_script(script_name)


@scripting_bp.route('/api/v2/vault/scripting/<script_name>', methods=['DELETE'])
def delete_script(script_name):
    return scripting.delete_script(script_name)


@scripting_bp.route('/api/v2/vault/scripting/<script_name>', methods=['PATCH'])
def call_script(script_name):
    return scripting.run_script(script_name)


@scripting_bp.route('/api/v2/vault/scripting/<script_name>/<target_did>@<target_app_did>/<params>', methods=['GET'])
def call_script_url(script_name, target_did, target_app_did, params):
    return scripting.run_script_url(script_name, target_did, target_app_did, params)


@scripting_bp.route('/api/v2/vault/scripting/stream/{transaction_id}', methods=['PUT'])
def upload_file(transaction_id):
    return scripting.upload_file(transaction_id)


@scripting_bp.route('/api/v2/vault/scripting/stream/{transaction_id}', methods=['GET'])
def download_file(transaction_id):
    return scripting.download_file(transaction_id)
