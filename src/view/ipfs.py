# -*- coding: utf-8 -*-

"""
The view of ipfs module for file saving and viewing.
"""
from flask import Blueprint, request

from src.modules.ipfs.ipfs import IpfsFiles
from src.utils.http_exception import BadRequestException

blueprint = Blueprint('ipfs', __name__)
ipfs_files = IpfsFiles()


def init_app(app, hive_setting):
    """ This will be called by application initializer. """
    app.register_blueprint(blueprint)


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
