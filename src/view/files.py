# -*- coding: utf-8 -*-

"""
The view of files module.
"""
from flask import Blueprint, request

from src.modules.files.files import Files
from src.utils.http_exception import BadRequestException

blueprint = Blueprint('node-files', __name__)
files = Files()


def init_app(app, hive_setting):
    """ This will be called by application initializer. """
    # global scripting
    # scripting = Scripting(app=app, hive_setting=hive_setting)
    app.register_blueprint(blueprint)


@blueprint.route('/api/v2/vault/node-files/<regex("(|[0-9a-zA-Z_/.]*)"):path>', methods=['GET'])
def reading_operation(path):
    """ Download/get the properties of/get the hash of the file, list the files of the folder.
    Download the content of the file by path if no URL parameter.

    .. :quickref: 04 Files; Download/properties/hash/list

    **Request**:

    .. sourcecode:: http

        None

    **Response OK**:

    .. sourcecode:: http

        HTTP/1.1 200 OK

    .. code-block:: json

        <The bytes of the content of the file.>

    **Response Error**:

    .. sourcecode:: http

        HTTP/1.1 400 Bad Request

    .. sourcecode:: http

        HTTP/1.1 401 Unauthorized

    .. sourcecode:: http

        HTTP/1.1 403 Forbidden

    .. sourcecode:: http

        HTTP/1.1 404 Not Found

    List the files of the directory by the path if the URL parameter is 'comp=children'.

    **Request**:

    .. sourcecode:: http

        None

    **Response OK**:

    .. sourcecode:: http

        HTTP/1.1 200 OK

    .. code-block:: json

        {
            “value”: [{
                “name”: “<path/to/res>”
                “is_file”: false,
                “size”: <Integer>
            }, {
                “name”: “<path/to/dir>”
                “is_file”: true
            }]
        }

    **Response Error**:

    .. sourcecode:: http

        HTTP/1.1 400 Bad Request

    .. sourcecode:: http

        HTTP/1.1 401 Unauthorized

    .. sourcecode:: http

        HTTP/1.1 403 Forbidden

    .. sourcecode:: http

        HTTP/1.1 404 Not Found

    Get the properties of the file by the path if the URL parameter is 'comp=metadata'.

    **Request**:

    .. sourcecode:: http

        None

    **Response OK**:

    .. sourcecode:: http

        HTTP/1.1 200 OK

    .. code-block:: json

        {
            “name”: <path/to/res>,
            “is_file”: <true: file, false: folder>,
            “size”: <size>,
            “created”: <created timestamp>
            “updated”: <updated timestamp>
        }

    **Response Error**:

    .. sourcecode:: http

        HTTP/1.1 400 Bad Request

    .. sourcecode:: http

        HTTP/1.1 401 Unauthorized

    .. sourcecode:: http

        HTTP/1.1 403 Forbidden

    .. sourcecode:: http

        HTTP/1.1 404 Not Found

    Get the hash of the file by the path if the URL parameter is 'comp=hash'.

    **Request**:

    .. sourcecode:: http

        None

    **Response OK**:

    .. sourcecode:: http

        HTTP/1.1 200 OK

    .. code-block:: json

        {
            "name": <the path of the file>
            “algorithm”: <“algorithm name: currently support SHA256”>
            "hash":  <SHA-256 computation value of the file content>
        }


    **Response Error**:

    .. sourcecode:: http

        HTTP/1.1 400 Bad Request

    .. sourcecode:: http

        HTTP/1.1 401 Unauthorized

    .. sourcecode:: http

        HTTP/1.1 403 Forbidden

    .. sourcecode:: http

        HTTP/1.1 404 Not Found

    """
    component = request.args.get('comp')
    if not component:
        return files.download_file(path)
    elif component == 'children':
        return files.list_folder(path)
    elif component == 'metadata':
        return files.get_properties(path)
    elif component == 'hash':
        return files.get_hash(path)
    else:
        return BadRequestException(msg='invalid parameter "comp"').get_error_response()


@blueprint.route('/api/v2/vault/node-files/<path:path>', methods=['PUT'])
def writing_operation(path):
    """ Copy or upload file by path.
    Copy the file by the path if the URL parameter is 'dest=<path/to/destination>'.

    .. :quickref: 04 Files; Copy/upload

    **Request**:

    .. sourcecode:: http

        None

    **Response OK**:

    .. sourcecode:: http

        HTTP/1.1 201 Created

    .. code-block:: json

        {
            “name”: “<path/to/destination>”
        }

    **Response Error**:

    .. sourcecode:: http

        HTTP/1.1 400 Bad Request

    .. sourcecode:: http

        HTTP/1.1 401 Unauthorized

    .. sourcecode:: http

        HTTP/1.1 403 Forbidden

    .. sourcecode:: http

        HTTP/1.1 404 Not Found

    .. sourcecode:: http

        HTTP/1.1 455 Already Exists

    Upload the content of the file by path if no URL parameter.

    **Request**:

    .. sourcecode:: http

        None

    **Response OK**:

    .. sourcecode:: http

        HTTP/1.1 201 Created

    .. code-block:: json

        {
            “name”: “<path/to/res>”
        }

    **Response Error**:

    .. sourcecode:: http

        HTTP/1.1 400 Bad Request

    .. sourcecode:: http

        HTTP/1.1 401 Unauthorized

    .. sourcecode:: http

        HTTP/1.1 403 Forbidden

    .. sourcecode:: http

        HTTP/1.1 404 Not Found

    """
    dest_path = request.args.get('dest')
    if dest_path:
        return files.copy_file(path, dest_path)
    return files.upload_file(path)


@blueprint.route('/api/v2/vault/node-files/<path:path>', methods=['PATCH'])
def move_file(path):
    """ Move the file by path to the file provided by the URL parameter 'to=<path/to/destination>'

    .. :quickref: 04 Files; Move

    **Request**:

    .. sourcecode:: http

        None

    **Response OK**:

    .. sourcecode:: http

        HTTP/1.1 200 OK

    .. code-block:: json

        {
            “name”: “<path/to/destination>”
        }

    **Response Error**:

    .. sourcecode:: http

        HTTP/1.1 400 Bad Request

    .. sourcecode:: http

        HTTP/1.1 401 Unauthorized

    .. sourcecode:: http

        HTTP/1.1 403 Forbidden

    .. sourcecode:: http

        HTTP/1.1 404 Not Found

    .. sourcecode:: http

        HTTP/1.1 455 Already Exists

    """
    dst_path = request.args.get('to')
    return files.move_file(path, dst_path)


@blueprint.route('/api/v2/vault/node-files/<path:path>', methods=['DELETE'])
def delete_file(path):
    """ Delete the file by path.

    .. :quickref: 04 Files; Delete

    **Request**:

    .. sourcecode:: http

        None

    **Response OK**:

    .. sourcecode:: http

        HTTP/1.1 204 No Content

    **Response Error**:

    .. sourcecode:: http

        HTTP/1.1 400 Bad Request

    .. sourcecode:: http

        HTTP/1.1 401 Unauthorized

    .. sourcecode:: http

        HTTP/1.1 403 Forbidden

    """
    return files.delete_file(path)
