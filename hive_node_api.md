# Hive node plus plus api

## Auth of did and app (there will be a new version)
1. User auth
```
HTTP: POST
URL: /api/v1/did/auth
Content-Type: "application/json"
data: {"jwt":" auth_token}
return:
    Success:
        {
          "_status":"OK",
          "subject": "didauth",
          "issuer": "elastos_hive_node",
          "token": access_token
          "exp": expiration_date
        }
    Failure:
        {
          "_status": "ERR",
          "_error": {
            "code": 401,
            "message": err_message
          }
        }
```

## Synchronization
1. Init synchronization from google drive
* If there is a new user auth of hive++, must call this api before any other data operation(mongoDB or file etc)
```
HTTP: POST
URL: /api/v1/sync/setup/google_drive
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data:
    {
      "token": "ya29.a0AfH6SMAVaP_gNAdbF25L5hktoPRdV8mBkcra6UaneG2w7ZYSusXevycqvhUrGrQ_FpsBPYYvxq2Sdx13zEwG1-m8I-pSFV05UY52X6wNnVlpxG7hsyBteEdUiiQPDT52zbK5ceQZ4-cpfXSlrplsQ8kZvPYC5nR1yks",
      "refresh_token": "1//06llFKBe-DBkRCgYIARAAGAYSNwF-L9Irfka2E6GP-J9gKBZN5AQS3z19vHOtjHq67p2ezCsJiVUZO-jKMSDKLgkiGfXgmBYimwc",
      "token_uri": "https://oauth2.googleapis.com/token",
      "client_id": "24235223939-7335upec07n0c3qc7mnd19jqoeglrg3t.apps.googleusercontent.com",
      "client_secret": "-7Ls5u1NpRe77Dy6VkL5W4pe",
      "scopes": [
        "https://www.googleapis.com/auth/drive.file"
      ],
      "expiry": "2020-06-24 03:10:49.960710"
    }
return:
    Success: {"_status":"OK"}
    Failure:
        {
          "_status": "ERR",
          "_error": {
            "code": 401,
            "message": "Error message"
          }
        }
comments: The input data is google oauth2 token to json, no need to change anything
```
# Database
WARNING: Not support mongoDB generate "_id" filter yet
- Create mongoDB collection
```json
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

- Delete mongoDB collection
```json
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

- Insert a new document in a given collection
    * collection: collection name.
    * document: The document to insert. Must be a mutable mapping type. If the document does not have an _id field one will be added automatically.
    * options:
        bypass_document_validation: (optional) If True, allows the write to opt-out of document level validation. Default is False.
```json
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


- Insert many new documents in a given collection
    * collection: collection name.
    * document: The document to insert. Must be a mutable mapping type. If the document does not have an _id field one will be added automatically.
    * options:
        * ordered (optional): If True (the default) documents will be inserted on the server serially, in the order provided. If an error occurs all remaining inserts are aborted. If False, documents will be inserted on the server in arbitrary order, possibly in parallel, and all document inserts will be attempted.
        * bypass_document_validation: (optional) If True, allows the write to opt-out of document level validation. Default is False.
```json
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

- Update an existing document in a given collection
    * collection: collection name.
    * filter: A query that matches the document to update.
    * update: The modifications to apply.
    * options:
        * upsert (optional): If True, perform an insert if no documents match the filter.
        * bypass_document_validation: (optional) If True, allows the write to opt-out of document level validation. Default is False. This option is only supported on MongoDB 3.2 and above.
```json
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

- Update many existing documents in a given collection
    * collection: collection name.
    * filter: A query that matches the document to update.
    * update: The modifications to apply.
    * options:
        * upsert (optional): If True, perform an insert if no documents match the filter.
        * bypass_document_validation: (optional) If True, allows the write to opt-out of document level validation. Default is False. This option is only supported on MongoDB 3.2 and above.
```json
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

- Delete an existing document in a given collection
    * collection: collection name.
    * filter: A query that matches the document to delete.
```json
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

- Delete many existing documents in a given collection
    * collection: collection name.
    * filter: A query that matches the document to delete.
```json
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

- Count documents
    * collection: collection name.
    * filter: The document of filter
    * options:
        * skip (int): The number of matching documents to skip before returning results.
        * limit (int): The maximum number of documents to count. Must be a positive integer. If not provided, no limit is imposed.
        * maxTimeMS (int): The maximum amount of time to allow this operation to run, in milliseconds.
```json
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

- Find a specific document(findOne)
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
```json
HTTP: POST
URL: /api/v1/db/find_one
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: 
    {
        "collection": "works",
        "options": {
            "filter": {
                "author": "john doe1_1"
            },
            "skip": 0,
            "projection": {‘_id’: false},
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
                "title": "Eve for Dummies1_1"
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

- Find all documents(findMany)
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
```json
HTTP: POST
URL: /api/v1/db/find_many
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: 
    {
        "collection": "works",
        "options": {
            "filter": {
                "author": "john doe1_1",
            },
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
                    "title": "Eve for Dummies1_1"
                },
                {
                    "author": "john doe1_1",
                    "title": "Eve for Dummies1_1"
                },
                {
                    "author": "john doe1_1",
                    "title": "Eve for Dummies1_1"
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

## File operation
1. Create folder
```
HTTP: POST
URL: /api/v1/files/creator/folder
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: {name="path/of/folder/name"}
return:
    Success: {"_status":"OK"}
    Failure:
        {
          "_status": "ERR",
          "_error": {
            "code": 401,
            "message": "Error message"
          }
        }
```

2. Create file
```
HTTP: POST
URL: /api/v1/files/creator/file
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: {name="path/of/file/name"}
return:
    Success:
        {
          "_status":"OK",
          "upload_file_url":"/api/v1/files/uploader/some/url"
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

3. Upload file
```
HTTP: POST
URL: Create file api return "upload_file_url"
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
data: file data
return:
    Success: {"_status":"OK"}
    Failure:
        {
          "_status": "ERR",
          "_error": {
            "code": 401,
            "message": "Error message"
          }
        }
```

4. Download file
```
HTTP: GET
URL: api/v1/files/downloader?name="file.name"
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
return:
    Success: file data
    Failure:
        {
          "_status": "ERR",
          "_error": {
            "code": 401,
            "message": "Error message"
          }
        }
comment: support content range
```

5. Delete file
```
HTTP: POST
URL: /api/v1/files/deleter/file
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: {"name": "test.png"}
return:
    Success: {"_status":"OK"}
    Failure:
        {
          "_status": "ERR",
          "_error": {
            "code": 401,
            "message": "Error message"
          }
        }
```

6. Delete folder
```
HTTP: POST
URL: /api/v1/files/deleter/folder
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: {"name": "test.png"}
return:
    Success: {"_status":"OK"}
    Failure:
        {
          "_status": "ERR",
          "_error": {
            "code": 401,
            "message": "Error message"
          }
        }
```

7. Move file or folder
```
HTTP: POST
URL: /api/v1/files/mover
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data:
    {
      "src_name": "path/of/src/folder/or/file",
      "dst_name": "path/of/dst/folder/or/file",
    }
return:
    Success: {"_status":"OK"}
    Failure:
        {
          "_status": "ERR",
          "_error": {
            "code": 401,
            "message": "Error message"
          }
        }
comment: usage like shell command "mv"
```

8. Copy file or folder
```
HTTP: POST
URL: /api/v1/files/copier
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data:
    {
      "src_name": "path/of/src/folder/or/file",
      "dst_name": "path/of/dst/folder/or/file",
    }
return:
    Success: {"_status":"OK"}
    Failure:
        {
          "_status": "ERR",
          "_error": {
            "code": 401,
            "message": "Error message"
          }
        }
comment: usage like shell command "cp"
```

9. Get properties of file or folder
```
HTTP: GET
URL: api/v1/files/properties?name="file.or.folder.name"
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
return:
    Success:
        {
          "_status": "OK",
          "st_ctime": 123012.2342,
          "st_mtime": 123012.2342,
          "st_atime": 123012.2342,
          "st_size": 230
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

10. List folder
```
HTTP: GET
URL: /api/v1/files/list/folder?name="folder.name"
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
return:
    Success:
        {
          "_status": "OK",
          "files": [
            "folder_name/",
            "filename",
            "test.png"
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

11. Get file hash(MD5)
```
HTTP: GET
URL: /api/v1/files/file/hash?name="file.name"
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
return:
    Success:
        {
          "_status": "OK",
          "MD5": "3a29a81d7b2718a588a5f6f3491b3c57"
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