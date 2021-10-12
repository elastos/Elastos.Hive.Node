# -*- coding: utf-8 -*-

"""
The view of database module.
"""
from flask import Blueprint
from src.modules.database.database import Database
from src.utils.http_exception import InvalidParameterException
from src.utils.http_request import params, rqargs

blueprint = Blueprint('database', __name__)
database: Database = None


def init_app(app):
    """ This will be called by application initializer. """
    global database
    database = Database()
    app.register_blueprint(blueprint)


@blueprint.route('/api/v2/vault/db/collections/<collection_name>', methods=['PUT'])
def create_collection(collection_name):
    """ Create the collection by collection name.

    .. :quickref: 03 Database; Create the collection

    **Request**:

    .. sourcecode:: http

        None

    **Response OK**:

    .. sourcecode:: http

        HTTP/1.1 200 OK

    .. code-block:: json

        {
            “name”: “<collection_name>”
        }

    **Response Error**:

    .. sourcecode:: http

        HTTP/1.1 400 Bad Request

    .. sourcecode:: http

        HTTP/1.1 401 Unauthorized

    .. sourcecode:: http

        HTTP/1.1 403 Forbidden

    .. sourcecode:: http

        HTTP/1.1 455 Already Exists

    """
    return database.create_collection(collection_name)


@blueprint.route('/api/v2/vault/db/<collection_name>', methods=['DELETE'])
def delete_collection(collection_name):
    """ Delete the collection by collection name.

    .. :quickref: 03 Database; Delete the collection

    **Request**:

    .. sourcecode:: http

        None

    **Response OK**:

    .. sourcecode:: http

        HTTP/1.1 204 No Content

    .. code-block:: json

        {
            “name”: “<collection_name>”
        }

    **Response Error**:

    .. sourcecode:: http

        HTTP/1.1 400 Bad Request

    .. sourcecode:: http

        HTTP/1.1 401 Unauthorized

    .. sourcecode:: http

        HTTP/1.1 403 Forbidden

    """
    return database.delete_collection(collection_name)


@blueprint.route('/api/v2/vault/db/collection/<collection_name>', methods=['POST'])
def insert_or_count_document(collection_name):
    """ Insert or count the documents. Insert the documents if no URL parameters.

    .. :quickref: 03 Database; Insert&count the documents

    **Request**:

    .. code-block:: json

        {
            "document": [
                {
                    "author": "john doe1",
                    "title": "Eve for Dummies1"
                },
                {
                    "author": "john doe2",
                    "title": "Eve for Dummies2"
                 }
             ],
            "options": {
                 "bypass_document_validation":false,
                 "ordered":true
             }
        }


    **Response OK**:

    .. sourcecode:: http

        HTTP/1.1 201 Created

    .. code-block:: json

        {
            "acknowledged": true,
            "inserted_ids": [
                "5f4658d122c95b17e72f2d4a",
                "5f4658d122c95b17e72f2d4b"
            ]
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

    Count the documents if the URL parameter is **op = count**

    **Request**:

    .. code-block:: json

        {
            "filter": {
                "author": "john doe1_1",
            },
            "options": {
                "skip": 0,
                "limit": 10,
                "maxTimeMS": 1000000000
            }
        }

    **Response OK**:

    .. sourcecode:: http

        HTTP/1.1 204 No Content

    .. code-block:: json

        {
            "count": 10
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

    """
    op, _ = rqargs.get_str('op')
    json_body, msg = params.get_root()
    if msg or not json_body:
        return InvalidParameterException(msg=f'Invalid request body.').get_error_response()
    if op == 'count':
        if 'filter' not in json_body or type(json_body.get('filter')) is not dict:
            return InvalidParameterException().get_error_response()
        return database.count_document(collection_name, json_body)
    if 'document' not in json_body or type(json_body.get('document')) != list:
        return InvalidParameterException().get_error_response()
    return database.insert_document(collection_name, json_body)


@blueprint.route('/api/v2/vault/db/collection/<collection_name>', methods=['PATCH'])
def update_document(collection_name):
    """ Update the documents by collection name.

    .. :quickref: 03 Database; Update the documents

    **URL Parameters**:

    .. sourcecode:: http

        updateone=<true|false> # Whether update only one matched document. Default is false.

    **Request**:

    .. code-block:: json

        {
            "filter": {
                "author": "john doe1",
            },
            "update": {"$set": {
                "author": "john doe1_1",
                "title": "Eve for Dummies1_1"
            }},
            "options": {
                "upsert": true,
                "bypass_document_validation": false
            }
        }

    **Response OK**:

    .. sourcecode:: http

        HTTP/1.1 200 OK

    .. code-block:: json

        {
            "acknowledged": true,
            "matched_count": 10,
            "modified_count": 10,
            "upserted_id": null
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

    """
    is_update_one, msg = rqargs.get_bool('updateone')
    if msg:
        return InvalidParameterException(msg=msg).get_error_response()
    json_body, msg = params.get_root()
    if msg or not json_body:
        return InvalidParameterException(msg=f'Invalid request body.').get_error_response()
    if 'filter' in json_body and type(json_body.get('filter')) is not dict:
        return InvalidParameterException(msg='Invalid parameter filter.').get_error_response()
    if 'update' not in json_body or type(json_body.get('update')) is not dict:
        return InvalidParameterException(msg='Invalid parameter update.').get_error_response()
    return database.update_document(collection_name, json_body, is_update_one)


@blueprint.route('/api/v2/vault/db/collection/<collection_name>', methods=['DELETE'])
def delete_document(collection_name):
    """ Delete the documents by collection name.

    .. :quickref: 03 Database; Delete the documents

    **URL Parameters**:

    .. sourcecode:: http

        deleteone=<true|false> # Whether delete only one matched document. Default is false.

    **Request**:

    .. code-block:: json

        {
            "filter": {
                "author": "john doe1",
            }
         }

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
    is_delete_one, msg = rqargs.get_bool('deleteone')
    if msg:
        return InvalidParameterException(msg=msg).get_error_response()
    col_filter, msg = params.get_dict('filter')
    if msg:
        return InvalidParameterException(msg=msg).get_error_response()
    return database.delete_document(collection_name, col_filter, is_delete_one)


@blueprint.route('/api/v2/vault/db/<collection_name>', methods=['GET'])
def find_document(collection_name):
    """ Find the documents by collection name. The parameters are URL ones.

    .. :quickref: 03 Database; Find the documents

    **URL Parameters**:

    .. sourcecode:: http

        filter (json str) : the filter doc need to be encoded by url
        skip (int):
        limit (int):

    **Request**:

    .. code-block:: json

        None

    **Response OK**:

    .. sourcecode:: http

        HTTP/1.1 200 OK

    .. code-block:: json

        {
            "items": [{
                "author": "john doe1_1",
                "title": "Eve for Dummies1_1",
                "created": {
                    "$date": 1630022400000
                },
                "modified": {
                    "$date": 1598803861786
                }
            }]
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

    """
    col_filter, msg = rqargs.get_dict('filter')
    if msg:
        return InvalidParameterException(msg=msg).get_error_response()
    skip, limit = rqargs.get_int('skip')[0], rqargs.get_int('limit')[0]
    if skip < 0 or limit < 0:
        return InvalidParameterException(msg='Invalid parameter skip or limit.').get_error_response()
    return database.find_document(collection_name, col_filter, skip, limit)


@blueprint.route('/api/v2/vault/db/query', methods=['POST'])
def query_document():
    """ Query the documents with more options

    .. :quickref: 03 Database; Query the documents

    **Request**:

    .. code-block:: json

        {
            "collection": "works",
            "filter": {
                "author": "john doe1_1",
            },
            "options": {
                "skip": 0,
                "limit": 3,
                "projection": {
                    "_id": false
                },
                "sort": [('_id', -1)], # pymongo.DESCENDING
                "allow_partial_results": false,
                "return_key": false,
                "show_record_id": false,
                "batch_size": 0
            }
        }

    **Response OK**:

    .. sourcecode:: http

        HTTP/1.1 201 Created

    .. code-block:: json

        {
            "items": [{
                "author": "john doe1_1",
                "title": "Eve for Dummies1_1",
                "created": {
                    "$date": 1630022400000
                },
                "modified": {
                    "$date": 1598803861786
                }
            },
            {
                "author": "john doe1_2",
                "title": "Eve for Dummies1_2",
                "created": {
                    "$date": 1630022400000
                },
                "modified": {
                    "$date": 1598803861786
                }
            }]
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

    """
    json_body, msg = params.get_root()
    if msg:
        return InvalidParameterException(msg=msg).get_error_response()
    if 'collection' not in json_body or not json_body['collection']:
        return InvalidParameterException(msg='No collection name in the request body.').get_error_response()
    if 'filter' not in json_body or type(json_body.get('filter')) is not dict:
        return InvalidParameterException(msg='Invalid parameter filter.').get_error_response()
    return database.query_document(json_body['collection'], json_body)
