# -*- coding: utf-8 -*-

"""
The view of database module.
"""
from flask_restful import Resource
from src.modules.database.database import Database
from src.utils.http_exception import InvalidParameterException
from src.utils.http_request import RV


class CreateCollection(Resource):
    def __init__(self):
        self.database = Database()

    def put(self, collection_name):
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

        .. sourcecode:: http

            HTTP/1.1 507 Insufficient Storage

        """

        collection_name = RV.get_value('collection_name', collection_name, str)

        return self.database.create_collection(collection_name)


class DeleteCollection(Resource):
    def __init__(self):
        self.database = Database()

    def delete(self, collection_name):
        """ Delete the collection by collection name.

        .. :quickref: 03 Database; Delete the collection

        **Request**:

        .. sourcecode:: http

            None

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

        collection_name = RV.get_value('collection_name', collection_name, str)

        return self.database.delete_collection(collection_name)


class InsertOrCount(Resource):
    def __init__(self):
        self.database = Database()

    def post(self, collection_name):
        """ Insert or count the documents.

        .. :quickref: 03 Database; Insert&count the documents

        Insert the documents if no URL parameters.

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
                "options": {  # optional
                    "bypass_document_validation": false,
                    "ordered": true,
                    # Default true. If true, new fields [created, modified: int(timestamp)] will be added to each document.
                    "timestamp": true
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

        .. sourcecode:: http

            HTTP/1.1 507 Insufficient Storage

        Count the documents if the URL parameter is **op=count**

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

            HTTP/1.1 404 Not Found

        """

        op = RV.get_args().get_opt('op', str, None)
        options = RV.get_body().get_opt('options', dict, {})

        if op is None:
            documents = RV.get_body().get('document', list)
            for doc in documents:
                if not isinstance(doc, dict):
                    raise InvalidParameterException('The element of "document" MUST "dict"')

            return self.database.insert_document(collection_name, documents, options)

        elif op == 'count':
            filter_ = RV.get_body().get('filter')

            return self.database.count_document(collection_name, filter_, options)

        else:
            raise InvalidParameterException('Invalid parameter "op"')


class Update(Resource):
    def __init__(self):
        self.database = Database()

    def patch(self, collection_name):
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
                # This will update modified field if exists.
                "update": {
                    "$set": {  # optional
                        "author": "john doe1_1",
                        "title": "Eve for Dummies1_1"
                    }
                },
                "options": {  # optional
                    "upsert": true,
                    "bypass_document_validation": false,
                    # Default true. If true, the field modified (if exists) will be updated to any matched documents.
                    "timestamp": true
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

        .. sourcecode:: http

            HTTP/1.1 507 Insufficient Storage

        """

        is_update_one = RV.get_args().get_opt('updateone', bool, False)
        filter_ = RV.get_body().get('filter')
        update = RV.get_body().get('update')
        RV.get_body().get('update').validate_opt('$set')
        options = RV.get_body().get_opt('options', dict, {})

        return self.database.update_document(collection_name, filter_, update, options, is_update_one)


class Delete(Resource):
    def __init__(self):
        self.database = Database()

    def delete(self, collection_name):
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

        is_delete_one = RV.get_args().get_opt('deleteone', bool, False)
        filter_ = RV.get_body().get('filter')

        return self.database.delete_document(collection_name, filter_, is_delete_one)


class Find(Resource):
    def __init__(self):
        self.database = Database()

    def get(self, collection_name):
        """ Find the documents by collection name. The parameters are URL ones.

        .. :quickref: 03 Database; Find the documents

        **URL Parameters**:

        .. sourcecode:: http

            filter: (json str)  # the filter doc need to be encoded by url
            skip: (int)         # optional
            limit: (int)        # optional

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

            HTTP/1.1 404 Not Found

        """

        filter_ = RV.get_args().get('filter')
        skip = RV.get_args().get_opt('skip', int, None)
        limit = RV.get_args().get_opt('limit', int, None)

        return self.database.find_document(collection_name, filter_, skip, limit)


class Query(Resource):
    def __init__(self):
        self.database = Database()

    def post(self):
        """ Query the documents with more options

        .. :quickref: 03 Database; Query the documents

        **Request**:

        .. code-block:: json

            {
                "collection": "works",
                "filter": {
                    "author": "john doe1_1",
                },
                "options": {  # optional
                    "skip": 0,
                    "limit": 3,
                    "projection": {
                        "_id": false
                    },
                    "sort": [["_id", -1]], # -1: pymongo.DESCENDING, 1: pymongo.ASCENDING
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

            HTTP/1.1 404 Not Found

        """

        collection_name = RV.get_body().get('collection', str)
        filter_ = RV.get_body().get('filter')
        options = RV.get_body().get_opt('options', dict, {})

        return self.database.query_document(collection_name, filter_, options)
