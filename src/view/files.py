# -*- coding: utf-8 -*-

"""
The view of files module.
"""
from flask import Blueprint, request

from src.modules.files.files import Files
from src.utils.http_response import BadRequestException

blueprint = Blueprint('subscription', __name__)
files = Files()


def init_app(app, hive_setting):
    """ This will be called by application initializer. """
    # global scripting
    # scripting = Scripting(app=app, hive_setting=hive_setting)
    app.register_blueprint(blueprint)


@blueprint.route('/api/v2/vault/files/<path>', methods=['PUT'])
def upload_file(path):
    dst_path = request.args.get('dst')
    if dst_path:
        return files.copy_file(path, dst_path)
    return files.upload_file(path)


@blueprint.route('/api/v2/vault/files/<path>', methods=['GET'])
def download_file(path):
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
        return BadRequestException(msg='invalid parameter "comp"')


@blueprint.route('/api/v2/vault/files/<path>', methods=['DELETE'])
def delete_file(path):
    return files.delete_file(path)


@blueprint.route('/api/v2/vault/files/<path>', methods=['PATCH'])
def move_file(path):
    dst_path = request.args.get('to')
    return files.move_file(path, dst_path)
