# -*- coding: utf-8 -*-

"""
The view of backup module.
"""
from flask import Blueprint, request

from src.modules.backup.backup import Backup
from src.utils.http_response import NotImplementedException

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
