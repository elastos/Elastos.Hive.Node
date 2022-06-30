# -*- coding: utf-8 -*-

"""
The view of ipfs module for files and scripting.
"""
from flask_restful import Resource

from src.modules.ipfs.ipfs_files import IpfsFiles
from src.utils.http_exception import InvalidParameterException
from src.utils.http_request import rqargs
from src.utils.http_response import response_stream


class ReadingOperation(Resource):
    def __init__(self):
        self.ipfs_files = IpfsFiles()

    @response_stream
    def get(self, path):
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

            HTTP/1.1 404 Not Found

        """

        component, _ = rqargs.get_str('comp')
        if not path and component != 'children':
            raise InvalidParameterException('Resource path is mandatory, but its missing.')

        if not component:
            return self.ipfs_files.download_file(path)
        elif component == 'children':
            return self.ipfs_files.list_folder(path)
        elif component == 'metadata':
            return self.ipfs_files.get_properties(path)
        elif component == 'hash':
            return self.ipfs_files.get_hash(path)
        else:
            raise InvalidParameterException(f'Unsupported parameter "comp" value {component}')


class WritingOperation(Resource):
    def __init__(self):
        self.ipfs_files = IpfsFiles()

    def put(self, path):
        """ Copy or upload file by path.
        Copy the file by the path if the URL parameter is 'dest=<path/to/destination>'.

        .. :quickref: 04 Files; Copy/upload

        Copy the file from 'path' to 'dest'.

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

        .. sourcecode:: http

            HTTP/1.1 507 Insufficient Storage

        Upload the content of the file by path if no URL parameter.

        **Request**:

        **URL Parameters**:

        .. sourcecode:: http

            public=<true|false>    # whether the file uploaded can be access anonymously.
            script_name=<string>   # script name used to set up for downloading by scripting module. the script can be run without params.
                                   # the executable name of the script is the same as the script name.

        **Response OK**:

        .. sourcecode:: http

            HTTP/1.1 200 OK

        .. code-block:: json

            {
                “name”: “<path/to/res>”,
                “cid”: “<cid>”  # the cid of ipfs proxy if public=true, else empty.
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

            HTTP/1.1 507 Insufficient Storage

        """

        if not path:
            raise InvalidParameterException('Resource path is mandatory, but its missing.')

        dst_path, _ = rqargs.get_str('dest')
        if not dst_path:
            is_public, msg = rqargs.get_bool('public', False)
            script_name, msg = rqargs.get_str('script_name', '')
            if is_public and not script_name:
                raise InvalidParameterException('MUST provide script name when public is true.')
            return self.ipfs_files.upload_file(path, is_public, script_name)

        if path == dst_path:
            raise InvalidParameterException(f'The source file {path} can be copied to a target file with same name')
        return self.ipfs_files.copy_file(path, dst_path)


class MoveFile(Resource):
    def __init__(self):
        self.ipfs_files = IpfsFiles()

    def patch(self, path):
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

        if not path:
            raise InvalidParameterException('Resource path is mandatory, but its missing.')

        dst_path, _ = rqargs.get_str('to')
        if not dst_path:
            raise InvalidParameterException('The path MUST be provided.')
        if path == dst_path:
            raise InvalidParameterException(f'The source file {path} can be moved to a target file with same name')
        return self.ipfs_files.move_file(path, dst_path)


class DeleteFile(Resource):
    def __init__(self):
        self.ipfs_files = IpfsFiles()

    def delete(self, path):
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

        .. sourcecode:: http

            HTTP/1.1 404 Not Found

        """

        if not path:
            raise InvalidParameterException('Resource path is mandatory, but its missing.')

        return self.ipfs_files.delete_file(path)
