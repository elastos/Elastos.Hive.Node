# -*- coding: utf-8 -*-

"""
The view of database module.
"""
from flask import Blueprint, request
from src.modules.database.database import Database
from src.utils.http_request import params

blueprint = Blueprint('database', __name__)
database = Database()


def init_app(app, hive_setting):
    """ This will be called by application initializer. """
    # global scripting
    # scripting = Scripting(app=app, hive_setting=hive_setting)
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

        HTTP/1.1 204 Deleted

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

        HTTP/1.1 204 Deleted

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
    op = request.args.get('op')
    if op == 'count':
        return database.count_document(collection_name, request.get_json(force=True, silent=True))
    return database.insert_document(collection_name, request.get_json(force=True, silent=True))


@blueprint.route('/api/v2/vault/db/collection/<collection_name>', methods=['PATCH'])
def update_document(collection_name):
    """ Update the documents by collection name.

    .. :quickref: 03 Database; Update the documents

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
    return database.update_document(collection_name, request.get_json(force=True, silent=True))


@blueprint.route('/api/v2/vault/db/collection/<collection_name>', methods=['DELETE'])
def delete_document(collection_name):
    """ Delete the documents by collection name.

    .. :quickref: 03 Database; Delete the documents

    **Request**:

    .. code-block:: json

        {
            "filter": {
                "author": "john doe1",
            }
         }

    **Response OK**:

    .. sourcecode:: http

        HTTP/1.1 204 Deleted

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
    return database.delete_document(collection_name, request.get_json(force=True, silent=True))


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
    return database.find_document(collection_name,
                                  request.args.get('filter'),
                                  request.args.get('skip'),
                                  request.args.get('limit'))


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
    json_body, collection_name = params.get2('collection')
    return database.query_document(collection_name, json_body)
