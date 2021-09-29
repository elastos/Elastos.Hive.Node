# -*- coding: utf-8 -*-

"""
The view of ipfs module for files and scripting.
"""
from flask import Blueprint, request

from src.modules.ipfs.ipfs_files import IpfsFiles
from src.utils.http_exception import BadRequestException, InvalidParameterException
from src.utils.http_request import rqargs

blueprint = Blueprint('ipfs-files', __name__)
ipfs_files = IpfsFiles()


def init_app(app, hive_setting):
    """ This will be called by application initializer. """
    app.register_blueprint(blueprint)


@blueprint.route('/api/v2/vault/files/<regex("(|[0-9a-zA-Z_/.]*)"):path>', methods=['GET'])
def reading_operation(path):
    component, _ = rqargs.get_str('comp')
    if not component:
        if not path:
            return InvalidParameterException(msg='Path MUST be provided.').get_error_response()
        return ipfs_files.download_file(path)
    elif component == 'children':
        return ipfs_files.list_folder(path)
    elif component == 'metadata':
        if not path:
            return InvalidParameterException(msg='The path MUST be provided.').get_error_response()
        return ipfs_files.get_properties(path)
    elif component == 'hash':
        if not path:
            return InvalidParameterException(msg='The path MUST be provided.').get_error_response()
        return ipfs_files.get_hash(path)
    else:
        return BadRequestException(msg='invalid parameter "comp"').get_error_response()


@blueprint.route('/api/v2/vault/files/<path:path>', methods=['PUT'])
def writing_operation(path):
    # INFO: The path will be definitely provided, otherwise return 405 outside this point.
    dst_path, _ = rqargs.get_str('dest')
    if dst_path:
        if path == dst_path:
            return InvalidParameterException(msg='The source filename and destination filename must not be same.') \
                .get_error_response()
        return ipfs_files.copy_file(path, dst_path)
    return ipfs_files.upload_file(path)


@blueprint.route('/api/v2/vault/files/<path:path>', methods=['PATCH'])
def move_file(path):
    # INFO: The path will be definitely provided, otherwise return 405 outside this point.
    dst_path, _ = rqargs.get_str('to')
    if not dst_path:
        return InvalidParameterException(msg='The path MUST be provided.').get_error_response()
    elif path == dst_path:
        return InvalidParameterException(msg='The source filename and destination filename must not be same.') \
                .get_error_response()
    return ipfs_files.move_file(path, dst_path)


@blueprint.route('/api/v2/vault/files/<path:path>', methods=['DELETE'])
def delete_file(path):
    # INFO: The path will be definitely provided, otherwise return 405 outside this point.
    return ipfs_files.delete_file(path)
