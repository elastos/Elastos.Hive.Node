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

blueprint = Blueprint('backup', __name__)
backup: Backup = None
server: BackupServer = None


def init_app(app, hive_setting):
    """ This will be called by application initializer. """
    global backup, server
    backup = Backup(app=app, hive_setting=hive_setting)
    server = BackupServer()
    app.register_blueprint(blueprint)


@blueprint.route('/api/v2/vault/content', methods=['GET'])
def get_state():
    return backup.get_state()


@blueprint.route('/api/v2/vault/content', methods=['POST'])
def backup_restore():
    to = request.args.get('to')
    fr = request.args.get('from')
    if to == 'hive_node':
        return backup.backup(params.get('credential'))
    elif fr == 'hive_node':
        return backup.restore(params.get('credential'))
    elif to == 'google_drive':
        raise NotImplementedException()
    elif fr == 'google_drive':
        raise NotImplementedException()


@blueprint.route('/api/v2/backup/promotion', methods=['POST'])
def promotion():
    return backup.promotion()

###############################################################################
# below is internal backup APIs


@blueprint.route(URL_BACKUP_SERVICE, methods=['GET'])
def internal_get_backup_service():
    return server.get_backup_service()


@blueprint.route(URL_BACKUP_FINISH, methods=['POST'])
def internal_backup_finish():
    return server.backup_finish(params.get('checksum_list'))


@blueprint.route(URL_BACKUP_FILES, methods=['GET'])
def internal_backup_files():
    return server.backup_files()


@blueprint.route(URL_BACKUP_FILE, methods=['GET'])
def internal_backup_get_file():
    return server.backup_get_file(request.args.get('file'))


@blueprint.route(URL_BACKUP_FILE, methods=['PUT'])
def internal_backup_upload_file():
    return server.backup_upload_file(request.args.get('file'))


@blueprint.route(URL_BACKUP_FILE, methods=['DELETE'])
def internal_backup_delete_file():
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
