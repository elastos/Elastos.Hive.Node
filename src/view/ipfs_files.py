# -*- coding: utf-8 -*-

"""
The view of ipfs module for files and scripting.
"""
from flask import Blueprint

from src.modules.ipfs.ipfs_files import IpfsFiles
from src.utils.http_exception import BadRequestException, InvalidParameterException
from src.utils.http_request import rqargs

blueprint = Blueprint('ipfs-files', __name__)
ipfs_files: IpfsFiles() = None


def init_app(app):
    """ This will be called by application initializer. """
    global ipfs_files
    ipfs_files = IpfsFiles()
    app.register_blueprint(blueprint)


@blueprint.route('/api/v2/vault/files/<regex("(|[0-9a-zA-Z_/.]*)"):path>', methods=['GET'])
def reading_operation(path):
    '''
    when no param 'comp' param is contained in request url, treat it as 'download' method.
    'download' method -  [GET] /api/v2/vault/files/<path:res>

    otherwise ([PUT] /api/v2/vault/files/<path:res>?comp=param)
    it would be treated as the following methods:
    'list'       method - The param 'comp' value is 'children';
    'properties' method - The param 'comp' value is 'metadata';
    'get_hash'   method - The param 'comp' value is 'hash'

    Notice: <path:path> should be provided, otherwise, it would return 405 to client.
    '''

    component, _ = rqargs.get_str('comp')
    if not path and component != 'children':
        return InvalidParameterException(msg='Resource path is mandatory, but its missing.').get_error_response()

    if not component:
        return ipfs_files.download_file(path)
    elif component == 'children':
        return ipfs_files.list_folder(path)
    elif component == 'metadata':
        return ipfs_files.get_properties(path)
    elif component == 'hash':
        return ipfs_files.get_hash(path)
    else:
        return BadRequestException(msg='Unsupported parameter "comp" value {comp}').get_error_response()

@blueprint.route('/api/v2/vault/files/<path:path>', methods=['PUT'])
def writing_operation(path):
    '''
    when no param 'dest' param is contained in request url, treat it as 'upload' method.
    otherwise, treat it as 'copy' method.

    Restful API:
    'copy'   method: [PUT] /api/v2/vault/files/<path:res>?dest=/path/to/dest
    'upload' method: [PUT] /api/v2/vault/files/<path:res>

    Notice: <path:path> should be provided, otherwise, it would return 405 to client.
    '''

    if not path:
        return InvalidParameterException(msg='Resource path is mandatory, but its missing.').get_error_response()

    param, _ = rqargs.get_str('dest')
    if not param:
        return ipfs_files.upload_file(path)

    if path == param:
        return InvalidParameterException(msg='The source file {path} can be copied to a target file with same name')\
            .get_error_response()
    return ipfs_files.copy_file(path, dst_path)

@blueprint.route('/api/v2/vault/files/<path:path>', methods=['PATCH'])
def move_file(path):
    '''
    This is the API to support 'move' method, must be with the URL below
    [PATCH] /api/v2/vault/files/<path:res>?dest=/path/to/dest

    Notice: <path:path> should be provided, otherwise, it would return 405 to client.
    '''
    if not path:
        return InvalidParameterException(msg='Resource path is mandatory, but its missing.').get_error_response()

    dst_path, _ = rqargs.get_str('to')
    if not dst_path:
        return InvalidParameterException(msg='The path MUST be provided.').get_error_response()
    if path == dst_path:
        return InvalidParameterException(msg='The source file {path} can be moved to a target file with same name') \
                .get_error_response()
    return ipfs_files.move_file(path, dst_path)


@blueprint.route('/api/v2/vault/files/<path:path>', methods=['DELETE'])
def delete_file(path):
    '''
    This is the API to support 'delete' method, must be with the URL below
    [DELETE] /api/v2/vault/files/<path:res>

    Notice: <path:path> should be provided, otherwise, it would return 405 to client.
    '''
    if not path:
        return InvalidParameterException(msg='Resource path is mandatory, but its missing.').get_error_response()

    return ipfs_files.delete_file(path)
