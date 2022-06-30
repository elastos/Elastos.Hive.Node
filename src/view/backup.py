# -*- coding: utf-8 -*-

"""
The view of ipfs-backup module for file saving and viewing.
"""
from flask_restful import Resource

from src.modules.ipfs.ipfs_backup_client import IpfsBackupClient
from src.modules.ipfs.ipfs_backup_server import IpfsBackupServer
from src.utils.http_exception import InvalidParameterException
from src.utils.http_request import params, rqargs


class State(Resource):
    def __init__(self):
        self.backup_client = IpfsBackupClient()

    def get(self):
        """ Get the status of the backup processing.

        .. :quickref: 06 Backup; Get the State

        **Request**:

        .. sourcecode:: http

            None

        **Response OK**:

        .. sourcecode:: http

            HTTP/1.1 200 OK

        .. code-block:: json

            {
                "state": "stop", # stop, backup, restore
                "result": "success" # success, failed, process
                "message": "" # any message for the result.
            }

        **Response Error**:

        .. sourcecode:: http

            HTTP/1.1 401 Unauthorized

        """
        return self.backup_client.get_state()


class BackupRestore(Resource):
    def __init__(self):
        self.backup_client = IpfsBackupClient()

    def post(self):
        """ Backup or restore the data of the vault service.

        Backup the data to another hive node by the credential if contains URL parameter is **to=hive_node**.

        .. :quickref: 06 Backup; Backup & Restore

        **Request**:

        .. code-block:: json

            {
               "credential":"<credential_string>"
            }

        **Response OK**:

        .. sourcecode:: http

            HTTP/1.1 201 Created

        **Response Error**:

        .. sourcecode:: http

            HTTP/1.1 400 Bad Request

        .. sourcecode:: http

            HTTP/1.1 401 Unauthorized

        .. sourcecode:: http

            HTTP/1.1 403 Forbidden

        .. sourcecode:: http

            HTTP/1.1 507 Insufficient Storage

        Restore the data from the other hive node if the URL parameter is **from=hive_node**.

        **Request**:

        .. code-block:: json

            {
               "credential":"<credential_string>"
            }

        **Response OK**:

        .. sourcecode:: http

            HTTP/1.1 201 Created

        **Response Error**:

        .. sourcecode:: http

            HTTP/1.1 400 Bad Request

        .. sourcecode:: http

            HTTP/1.1 401 Unauthorized

        .. sourcecode:: http

            HTTP/1.1 403 Forbidden

        .. sourcecode:: http

            HTTP/1.1 507 Insufficient Storage

        """
        to, fr, is_force = rqargs.get_str('to')[0], rqargs.get_str('from')[0], rqargs.get_bool('is_force')[0]
        credential, msg = params.get_str('credential')
        if msg or not credential:
            raise InvalidParameterException('Invalid parameter.')
        if to == 'hive_node':
            return self.backup_client.backup(credential, is_force)
        elif fr == 'hive_node':
            return self.backup_client.restore(credential, is_force)
        else:
            raise InvalidParameterException('Invalid parameter, to or fr need be set.')


###############################################################################
# ipfs-promotion on the backup server side
###############################################################################


class ServerPromotion(Resource):
    def __init__(self):
        self.backup_server = IpfsBackupServer()

    def post(self):
        """ Promote a backup service to the vault service on backup node.

        .. :quickref: 06 Backup; Promote

        **Request**:

        .. sourcecode:: http

            None

        **Response OK**:

        .. sourcecode:: http

            HTTP/1.1 200 OK

        **Response Error**:

        .. sourcecode:: http

            HTTP/1.1 401 Unauthorized

        .. sourcecode:: http

            HTTP/1.1 404 Not Found

        .. sourcecode:: http

            HTTP/1.1 455 Already Exists

        .. sourcecode:: http

            HTTP/1.1 507 Insufficient Storage

        """
        return self.backup_server.promotion()


###############################################################################
# ipfs-backup internal APIs on the backup server side
###############################################################################


class ServerInternalBackup(Resource):
    def __init__(self):
        self.backup_server = IpfsBackupServer()

    def post(self):
        return self.backup_server.internal_backup(params.get_str('cid')[0],
                                                  params.get_str('sha256')[0],
                                                  params.get_int('size')[0],
                                                  params.get_bool('is_force')[0])


class ServerInternalState(Resource):
    def __init__(self):
        self.backup_server = IpfsBackupServer()

    def get(self):
        return self.backup_server.internal_backup_state()


class ServerInternalRestore(Resource):
    def __init__(self):
        self.backup_server = IpfsBackupServer()

    def get(self):
        return self.backup_server.internal_restore()
