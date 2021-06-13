# -*- coding: utf-8 -*-

"""
The view of backup module.
"""
from flask import Blueprint, request

from src.modules.backup.backup import Backup
from src.utils.http_request import params
from src.utils.http_response import NotImplementedException
from src.view import URL_BACKUP_SERVICE, URL_BACKUP_FINISH, URL_BACKUP_FILES, URL_BACKUP_FILE, URL_BACKUP_PATCH_HASH, \
    URL_BACKUP_PATCH_FILE, URL_RESTORE_FINISH

blueprint = Blueprint('backup', __name__)
backup = Backup()


def init_app(app, hive_setting):
    """ This will be called by application initializer. """
    global backup
    backup = Backup(app=app, hive_setting=hive_setting)
    app.register_blueprint(blueprint)


@blueprint.route('/api/v2/vault/content', methods=['GET'])
def get_state():
    return backup.get_state()


@blueprint.route('/api/v2/vault/content', methods=['POST'])
def backup_restore():
    to = request.args.get('to')
    fr = request.args.get('from')
    if to == 'hive_node':
        return backup.backup(request.get_json(silent=True, force=True).get('credential'))
    elif fr == 'hive_node':
        return backup.restore(request.get_json(silent=True, force=True).get('credential'))
    elif to == 'google_drive':
        raise NotImplementedException()
    elif fr == 'google_drive':
        raise NotImplementedException()


@blueprint.route('/api/v2/backup/promotion', methods=['POST'])
def promotion():
    return backup.promotion()


@blueprint.route(URL_BACKUP_SERVICE, methods=['GET'])
def internal_backup_service():
    return backup.backup_service()


@blueprint.route(URL_BACKUP_FINISH, methods=['POST'])
def internal_backup_finish():
    return backup.backup_finish(params.get('checksum_list'))


@blueprint.route(URL_BACKUP_FILES, methods=['GET'])
def internal_backup_files():
    return backup.backup_files()


@blueprint.route(URL_BACKUP_FILE, methods=['GET'])
def internal_backup_get_file():
    return backup.backup_get_file(request.args.get('file'))


@blueprint.route(URL_BACKUP_FILE, methods=['PUT'])
def internal_backup_upload_file():
    return backup.backup_upload_file(request.args.get('file'))


@blueprint.route(URL_BACKUP_FILE, methods=['DELETE'])
def internal_backup_delete_file():
    return backup.backup_delete_file(request.args.get('file'))


@blueprint.route(URL_BACKUP_PATCH_HASH, methods=['GET'])
def internal_backup_get_file_hash():
    return backup.backup_get_file_hash(request.args.get('file'))


@blueprint.route(URL_BACKUP_PATCH_FILE, methods=['POST'])
def internal_backup_patch_file():
    return backup.backup_patch_file(request.args.get('file'))


@blueprint.route(URL_RESTORE_FINISH, methods=['POST'])
def internal_restore_finish():
    pass
