# -*- coding: utf-8 -*-

"""
The view of database module.
"""
from flask import Blueprint, request
from src.modules.database.database import Database

from src.utils.http_response import BadRequestException

blueprint = Blueprint('database', __name__)
database = Database()


def init_app(app, hive_setting):
    """ This will be called by application initializer. """
    # global scripting
    # scripting = Scripting(app=app, hive_setting=hive_setting)
    app.register_blueprint(blueprint)


@blueprint.route('/api/v2/vault/db/collections/<collection_name>', methods=['PUT'])
def create_collection(collection_name):
    return database.create_collection(collection_name)


@blueprint.route('/api/v2/vault/db/<collection_name>', methods=['DELETE'])
def delete_collection(collection_name):
    return database.delete_collection(collection_name)


@blueprint.route('/api/v2/vault/db/collection/<collection_name>', methods=['POST'])
def insert_document(collection_name):
    return database.insert_document(collection_name, request.get_json(force=True, silent=True))


@blueprint.route('/api/v2/vault/db/collection/<collection_name>', methods=['PATCH'])
def update_document(collection_name):
    return database.update_document(collection_name, request.get_json(force=True, silent=True))


@blueprint.route('/api/v2/vault/db/collection/<collection_name>', methods=['DELETE'])
def delete_document(collection_name):
    return database.delete_document(collection_name, request.get_json(force=True, silent=True))


@blueprint.route('/api/v2/vault/db/collection/<collection_name>', methods=['GET'])
def count_document(collection_name):
    op = request.args.get('op')
    if op == 'count':
        return database.count_document(collection_name, request.get_json(force=True, silent=True))
    else:
        return BadRequestException(msg='Invalid parameter "op"').get_error_response()


@blueprint.route('/api/v2/vault/db/<collection_name>', methods=['GET'])
def find_document(collection_name):
    return database.find_document(collection_name,
                                  request.args.get('filter'),
                                  request.args.get('skip'),
                                  request.args.get('limit'))


@blueprint.route('/api/v2/vault/db/query', methods=['POST'])
def query_document():
    json_body = request.get_json(force=True, silent=True)
    if not json_body:
        return BadRequestException(msg='Request body empty.').get_error_response()
    collection_name = json_body.get('collection')
    return database.query_document(collection_name, json_body)
