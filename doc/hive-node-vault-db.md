# Vault database
WARNING: Not support mongoDB generate "_id" filter yet
## Create mongoDB collection
```YAML
HTTP: POST
URL: /api/v1/db/create_collection
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data:
    {
      "collection": "works",
    }
return:
    Success:
        {
          "_status": "OK",
        }
    Failure:
        {
          "_status": "ERR",
          "_error": {
            "code": 401,
            "message": "Error message"
          }
        }
comments: "collection" is collection name of user's mongoDB.
```

## Delete mongoDB collection
```YAML
HTTP: POST
URL: /api/v1/db/delete_collection
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data:
    {
      "collection": "works",
    }
return:
    Success:
        {
          "_status": "OK",
        }
    Failure:
        {
          "_status": "ERR",
          "_error": {
            "code": 401,
            "message": "Error message"
          }
        }
comments: "collection" is collection name of user's mongoDB.
```

## Insert a new document in a given collection
    * collection: collection name.
    * document: The document to insert. Must be a mutable mapping type. If the document does not have an _id field one will be added automatically.
    * options:
        bypass_document_validation: (optional) If True, allows the write to opt-out of document level validation. Default is False.
```YAML
HTTP: POST
URL: /api/v1/db/insert_one
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data:
    {
      "collection": "works",
      "document": {
        "author": "john doe1",
        "title": "Eve for Dummies2"
      },
      "options": {"bypass_document_validation":false}
    }
return:
    Success:
        {
          "_status": "OK",
          "acknowledged": true,
          "inserted_id": "5edddab688db87875fddc3a5"
        }
    Failure:
        {
          "_status": "ERR",
          "_error": {
            "code": 401,
            "message": "Error message"
          }
        }
```

## Insert many new documents in a given collection
    * collection: collection name.
    * document: The document to insert. Must be a mutable mapping type. If the document does not have an _id field one will be added automatically.
    * options:
        * ordered (optional): If True (the default) documents will be inserted on the server serially, in the order provided. If an error occurs all remaining inserts are aborted. If False, documents will be inserted on the server in arbitrary order, possibly in parallel, and all document inserts will be attempted.
        * bypass_document_validation: (optional) If True, allows the write to opt-out of document level validation. Default is False.
```YAML
HTTP: POST
URL: /api/v1/db/insert_many
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data:
    {
      "collection": "works",
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
return:
    Success:
       {
        "_status": "OK",
        "acknowledged": true,
        "inserted_ids": [
            "5f4658d122c95b17e72f2d4a",
            "5f4658d122c95b17e72f2d4b"
        ]
        }
    Failure:
        {
          "_status": "ERR",
          "_error": {
            "code": 401,
            "message": "Error message"
          }
        }
```

## Update an existing document in a given collection
    * collection: collection name.
    * filter: A query that matches the document to update.
    * update: The modifications to apply.
    * options:
        * upsert (optional): If True, perform an insert if no documents match the filter.
        * bypass_document_validation: (optional) If True, allows the write to opt-out of document level validation. Default is False. This option is only supported on MongoDB 3.2 and above.
```YAML
HTTP: POST
URL: /api/v1/db/update_one
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data:
    {
      "collection": "works",
      "filter": {
        "author": "john doe3",
      },
      "update": {"$set": {
        "author": "john doe3_1",
        "title": "Eve for Dummies3_1"
      }},
      "options": {
          "upsert": true,
          "bypass_document_validation": false
      }
    }
return:
    Success:
        {
            "_status": "OK",
            "acknowledged": true,
            "matched_count": 1,
            "modified_count": 0,
            "upserted_id": null
        }
    Failure:
        {
          "_status": "ERR",
          "_error": {
            "code": 401,
            "message": "Error message"
          }
        }
```

## Update many existing documents in a given collection
    * collection: collection name.
    * filter: A query that matches the document to update.
    * update: The modifications to apply.
    * options:
        * upsert (optional): If True, perform an insert if no documents match the filter.
        * bypass_document_validation: (optional) If True, allows the write to opt-out of document level validation. Default is False. This option is only supported on MongoDB 3.2 and above.
```YAML
HTTP: POST
URL: /api/v1/db/update_many
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data:
    {
      "collection": "works",
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
return:
    Success:
    {
        "_status": "OK",
        "acknowledged": true,
        "matched_count": 10,
        "modified_count": 10,
        "upserted_id": null
    }
    Failure:
        {
          "_status": "ERR",
          "_error": {
            "code": 401,
            "message": "Error message"
          }
        }
```

## Delete an existing document in a given collection
    * collection: collection name.
    * filter: A query that matches the document to delete.
```YAML
HTTP: POST
URL: /api/v1/db/delete_one
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data:
    {
        "collection": "works",
        "filter": {
            "author": "john doe3_1",
        }
    }

return:
    Success:
    {
        "_status": "OK",
        "acknowledged": true,
        "deleted_count": 1,
    }
    Failure:
        {
          "_status": "ERR",
          "_error": {
            "code": 401,
            "message": "Error message"
          }
        }
```

## Delete many existing documents in a given collection
    * collection: collection name.
    * filter: A query that matches the document to delete.
```YAML
HTTP: POST
URL: /api/v1/db/delete_many
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data:
    {
        "collection": "works",
        "filter": {
            "author": "john doe1",
        }
    }
return:
    Success:
    {
        "_status": "OK",
        "acknowledged": true,
        "deleted_count": 0,
    }
    Failure:
        {
          "_status": "ERR",
          "_error": {
            "code": 401,
            "message": "Error message"
          }
        }
```

## Count documents
    * collection: collection name.
    * filter: The document of filter
    * options:
        * skip (int): The number of matching documents to skip before returning results.
        * limit (int): The maximum number of documents to count. Must be a positive integer. If not provided, no limit is imposed.
        * maxTimeMS (int): The maximum amount of time to allow this operation to run, in milliseconds.
```YAML
HTTP: POST
URL: /api/v1/db/count_documents
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data:
    {
        "collection": "works",
        "filter": {
            "author": "john doe1_1",
        },
        "options": {
            "skip": 0,
            "limit": 10,
            "maxTimeMS": 1000000000
        }
    }
return:
    Success:
    {
        "_status": "OK",
        "count": 10
    }
    Failure:
        {
          "_status": "ERR",
          "_error": {
            "code": 401,
            "message": "Error message"
          }
        }
```

## Find a specific document(findOne)
    * collection: collection name.
    * options():
        * filter (optional): a SON object specifying elements which must be present for a document to be included in the result set
        * projection (optional): a list of field names that should be returned in the result set or a dict specifying the fields to include or exclude. If projection is a list “_id” will always be returned. Use a dict to exclude fields from the result (e.g. projection={‘_id’: False}).
        * skip (optional): the number of documents to omit (from the start of the result set) when returning the results
        * sort  (optional): a list of (key, direction) pairs specifying the sort order for this query.
            ```
            {'field1': 'asc',
            'field2': 'desc'}
            ```
        * allow_partial_results (optional): if True, mongos will return partial results if some shards are down instead of returning an error.
        * return_key (optional): If True, return only the index keys in each document.
        * show_record_id (optional): If True, adds a field $recordId in each document with the storage engine’s internal record identifier.
        * batch_size (optional): Limits the number of documents returned in a single batch.
```YAML
HTTP: POST
URL: /api/v1/db/find_one
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data:
    {
        "collection": "works",
        "filter": {
          "author": "john doe1_1"
        },
        "options": {
            "skip": 0,
            "projection": {"_id": false},
            "sort": {"_id": "desc"},
            "allow_partial_results": false,
            "return_key": false,
            "show_record_id": false,
            "batch_size": 0
        }
    }
return:
    Success:
        {
          "_status": "OK",
          "items": {
            "author": "john doe1_1",
            "title": "Eve for Dummies1_1",
            "created": {
              "$date": 1630022400000
            },
            "modified": {
              "$date": 1598803861786
            }
          }
        }
    Failure:
        {
          "_status": "ERR",
          "_error": {
            "code": 401,
            "message": "Error message"
          }
        }
```

## Find all documents(findMany)
    * collection: collection name.
    * options:
        * filter (optional): a SON object specifying elements which must be present for a document to be included in the result set
        * projection (optional): a list of field names that should be returned in the result set or a dict specifying the fields to include or exclude. If projection is a list “_id” will always be returned. Use a dict to exclude fields from the result (e.g. projection={‘_id’: False}).
        * skip (optional): the number of documents to omit (from the start of the result set) when returning the results
        * limit (optional): the maximum number of results to return. A limit of 0 (the default) is equivalent to setting no limit.
        * sort  (optional): a list of (key, direction) pairs specifying the sort order for this query.
            ```
            {'field1': 'asc',
            'field2': 'desc'}
            ```
        * allow_partial_results (optional): if True, mongos will return partial results if some shards are down instead of returning an error.
        * return_key (optional): If True, return only the index keys in each document.
        * show_record_id (optional): If True, adds a field $recordId in each document with the storage engine’s internal record identifier.
        * batch_size (optional): Limits the number of documents returned in a single batch.
```YAML
HTTP: POST
URL: /api/v1/db/find_many
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data:
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
            "sort": {
                "_id": "desc"
            },
            "allow_partial_results": false,
            "return_key": false,
            "show_record_id": false,
            "batch_size": 0
        }
    }
return:
    Success:
        {
          "_status": "OK",
          "items": [
            {
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
            }
          ]
        }
    Failure:
        {
          "_status": "ERR",
          "_error": {
            "code": 401,
            "message": "Error message"
          }
        }
```

