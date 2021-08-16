# -*- coding: utf-8 -*-

"""
The view of ipfs module for file saving and viewing.
"""
import json

from flask import Blueprint, request

from src.modules.ipfs.ipfs import IpfsFiles
from src.modules.scripting.scripting import Scripting
from src.utils.http_exception import BadRequestException

blueprint = Blueprint('ipfs', __name__)
ipfs_files = IpfsFiles()
scripting = Scripting(is_ipfs=True)


def init_app(app, hive_setting):
    """ This will be called by application initializer. """
    global scripting
    scripting = Scripting(app=app, hive_setting=hive_setting, is_ipfs=True)
    app.register_blueprint(blueprint)


# ipfs-files


@blueprint.route('/api/v2/vault/ipfs-files/<regex("(|[0-9a-zA-Z_/.]*)"):path>', methods=['GET'])
def reading_operation(path):
    component = request.args.get('comp')
    if not component:
        return ipfs_files.download_file(path)
    elif component == 'children':
        return ipfs_files.list_folder(path)
    elif component == 'metadata':
        return ipfs_files.get_properties(path)
    elif component == 'hash':
        return ipfs_files.get_hash(path)
    else:
        return BadRequestException(msg='invalid parameter "comp"').get_error_response()


@blueprint.route('/api/v2/vault/ipfs-files/<path:path>', methods=['PUT'])
def writing_operation(path):
    dest_path = request.args.get('dest')
    if dest_path:
        return ipfs_files.copy_file(path, dest_path)
    return ipfs_files.upload_file(path)


@blueprint.route('/api/v2/vault/ipfs-files/<path:path>', methods=['PATCH'])
def move_file(path):
    dst_path = request.args.get('to')
    return ipfs_files.move_file(path, dst_path)


@blueprint.route('/api/v2/vault/ipfs-files/<path:path>', methods=['DELETE'])
def delete_file(path):
    return ipfs_files.delete_file(path)


# ipfs-scripting


@blueprint.route('/api/v2/vault/ipfs-scripting/<script_name>', methods=['PATCH'])
def call_script(script_name):
    return scripting.run_script(script_name)


@blueprint.route('/api/v2/vault/ipfs-scripting/<script_name>/<context_str>/<params>', methods=['GET'])
def call_script_url(script_name, context_str, params):
    target_did, target_app_did = None, None
    parts = context_str.split('@')
    if len(parts) == 2 and parts[0] and parts[1]:
        target_did, target_app_did = parts[0], parts[1]
    return scripting.run_script_url(script_name, target_did, target_app_did, json.loads(params))


@blueprint.route('/api/v2/vault/ipfs-scripting/stream/<transaction_id>', methods=['PUT'])
def upload_file(transaction_id):
    return scripting.upload_file(transaction_id)


@blueprint.route('/api/v2/vault/ipfs-scripting/stream/<transaction_id>', methods=['GET'])
def download_file(transaction_id):
    return scripting.download_file(transaction_id)
