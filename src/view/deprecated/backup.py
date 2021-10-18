# -*- coding: utf-8 -*-

"""
The view of backup module.
"""
from flask import Blueprint, request

from src.modules.backup.backup import Backup
from src.modules.backup.backup_server import BackupServer
from src.utils.http_request import params
from src.utils.http_exception import NotImplementedException
from src.utils.consts import URL_BACKUP_SERVICE, URL_BACKUP_FINISH, URL_BACKUP_FILES, URL_BACKUP_FILE, \
    URL_BACKUP_PATCH_HASH, URL_BACKUP_PATCH_FILE, URL_RESTORE_FINISH, URL_BACKUP_PATCH_DELTA

blueprint = Blueprint('backup-deprecated', __name__)
backup: Backup = None
server: BackupServer = None


def init_app(app):
    """ This will be called by application initializer. """
    global backup, server
    backup, server = Backup(), BackupServer()
    app.register_blueprint(blueprint)


@blueprint.route('/api/v2/vault-deprecated/content', methods=['GET'])
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
    return backup.get_state()


@blueprint.route('/api/v2/vault-deprecated/content', methods=['POST'])
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
    to = request.args.get('to')
    fr = request.args.get('from')
    if to == 'hive_node':
        return backup.backup(params.get_str('credential')[0])
    elif fr == 'hive_node':
        return backup.restore(params.get_str('credential')[0])
    elif to == 'google_drive':
        raise NotImplementedException()
    elif fr == 'google_drive':
        raise NotImplementedException()


@blueprint.route('/api/v2/backup-deprecated/promotion', methods=['POST'])
def promotion():
    return backup.promotion()

###############################################################################
# Below is internal backup APIs, provided by the backup server.


@blueprint.route(URL_BACKUP_SERVICE, methods=['GET'])
def internal_get_backup_service():
    """ Get the information of the backup service """
    return server.get_backup_service()


@blueprint.route(URL_BACKUP_FINISH, methods=['POST'])
def internal_backup_finish():
    """ Notify the backup service the process has been completed.
    The backup service will verify the checksum list of the files. """
    return server.backup_finish(params.get_list('checksum_list')[0])


@blueprint.route(URL_BACKUP_FILES, methods=['GET'])
def internal_backup_files():
    """ Get the checksum list of the files for compare on client side. """
    return server.backup_files()


@blueprint.route(URL_BACKUP_FILE, methods=['GET'])
def internal_backup_get_file():
    """ Get the content of the file """
    return server.backup_get_file(request.args.get('file'))


@blueprint.route(URL_BACKUP_FILE, methods=['PUT'])
def internal_backup_upload_file():
    """ Upload the content of the file to backup server """
    return server.backup_upload_file(request.args.get('file'))


@blueprint.route(URL_BACKUP_FILE, methods=['DELETE'])
def internal_backup_delete_file():
    """ Delete the file by the name """
    return server.backup_delete_file(request.args.get('file'))


@blueprint.route(URL_BACKUP_PATCH_HASH, methods=['GET'])
def internal_backup_get_file_hash():
    return server.backup_get_file_hash(request.args.get('file'))


@blueprint.route(URL_BACKUP_PATCH_DELTA, methods=['POST'])
def internal_backup_get_file_delta():
    return server.backup_get_file_delta(request.args.get('file'))


@blueprint.route(URL_BACKUP_PATCH_FILE, methods=['POST'])
def internal_backup_patch_file():
    return server.backup_patch_file(request.args.get('file'))


@blueprint.route(URL_RESTORE_FINISH, methods=['GET'])
def internal_restore_finish():
    return server.restore_finish()
