# -*- coding: utf-8 -*-

"""
The view of ipfs-backup module for file saving and viewing.
"""
from flask import Blueprint

from src.modules.ipfs.ipfs_backup_client import IpfsBackupClient
from src.modules.ipfs.ipfs_backup_server import IpfsBackupServer
from src.utils.consts import URL_IPFS_BACKUP_SERVER_BACKUP, URL_IPFS_BACKUP_SERVER_BACKUP_STATE, \
    URL_IPFS_BACKUP_SERVER_RESTORE
from src.utils.http_exception import InvalidParameterException
from src.utils.http_request import params, rqargs

blueprint = Blueprint('backup', __name__)
backup_client: IpfsBackupClient = None
backup_server: IpfsBackupServer = None


def init_app(app):
    """ This will be called by application initializer. """
    global backup_client, backup_server
    backup_client, backup_server = IpfsBackupClient(), IpfsBackupServer()
    app.register_blueprint(blueprint)


@blueprint.route('/api/v2/vault/content', methods=['GET'])
def get_state():
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

    .. sourcecode:: http

        HTTP/1.1 403 Forbidden

    """
    return backup_client.get_state()


@blueprint.route('/api/v2/vault/content', methods=['POST'])
def backup_restore():
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

    """
    to, fr, is_force = rqargs.get_str('to')[0], rqargs.get_str('from')[0], rqargs.get_bool('is_force')[0]
    credential, msg = params.get_str('credential')
    if msg or not credential:
        return InvalidParameterException(msg='Invalid parameter.').get_error_response()
    if to == 'hive_node':
        return backup_client.backup(credential, is_force)
    elif fr == 'hive_node':
        return backup_client.restore(credential, is_force)
    else:
        return InvalidParameterException(msg='Invalid parameter, to or fr need be set.').get_error_response()


# ipfs-promotion on the backup server side


@blueprint.route('/api/v2/backup/promotion', methods=['POST'])
def promotion():
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

        HTTP/1.1 403 Forbidden

    .. sourcecode:: http

        HTTP/1.1 404 Not Found

    .. sourcecode:: http

        HTTP/1.1 455 Already Exists

    .. sourcecode:: http

        HTTP/1.1 507 Insufficient Storage

    """
    return backup_server.promotion()


# ipfs-backup internal APIs on the backup server side


@blueprint.route(URL_IPFS_BACKUP_SERVER_BACKUP, methods=['POST'])
def internal_backup():
    return backup_server.internal_backup(params.get_str('cid')[0],
                                         params.get_str('sha256')[0],
                                         params.get_int('size')[0],
                                         params.get_bool('is_force')[0])


@blueprint.route(URL_IPFS_BACKUP_SERVER_BACKUP_STATE, methods=['GET'])
def internal_backup_state():
    return backup_server.internal_backup_state()


@blueprint.route(URL_IPFS_BACKUP_SERVER_RESTORE, methods=['GET'])
def internal_restore():
    return backup_server.internal_restore()
