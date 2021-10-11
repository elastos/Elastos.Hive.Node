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

blueprint = Blueprint('ipfs-backup', __name__)
backup_client = IpfsBackupClient()
backup_server = IpfsBackupServer()


def init_app(app):
    """ This will be called by application initializer. """
    app.register_blueprint(blueprint)


@blueprint.route('/api/v2/vault/content', methods=['GET'])
def get_state():
    return backup_client.get_state()


@blueprint.route('/api/v2/vault/content', methods=['POST'])
def backup_restore():
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


# subscription


@blueprint.route('/api/v2/subscription/backup', methods=['PUT'])
def backup_subscribe():
    return backup_server.subscribe()


@blueprint.route('/api/v2/subscription/backup', methods=['DELETE'])
def backup_unsubscribe():
    return backup_server.unsubscribe()


@blueprint.route('/api/v2/subscription/backup', methods=['GET'])
def backup_get_info():
    return backup_server.get_info()
