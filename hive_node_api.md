# Hive node plus plus api

## Table of Contents
- [Auth of did and app](#auth-of-did-and-app)
- [Synchronization](#synchronization)
- [Vault File](#vault-file)
- [Database](#database)
- [Scripting](#scripting)

## Auth of did and app
- User auth access request
```json
HTTP: POST
URL: /api/v1/did/sign_in
Content-Type: "application/json"
data: {"document": did_document}
return:
    Success:
        {
          "_status":"OK",
          "challenge": jwt,
        }
    Failure:
        {
          "_status": "ERR",
          "_error": {
            "code": 401,
            "message": err_message
          }
        }
comments: jwt include "nonce"
```
- User auth
```
HTTP: POST
URL: /api/v1/did/auth
Content-Type: "application/json"
data: {"jwt": "auth_token"}
return:
    Success:
        {
          "_status":"OK",
          "token": access_token,
        }
    Failure:
        {
          "_status": "ERR",
          "_error": {
            "code": 401,
            "message": "err_message"
          }
        }
comments: access_token is a "token", and it is a jwt too.
```

## Synchronization
- Init synchronization from google drive
* If there is a new user auth of hive++, must call this api before any other data operation(mongoDB or file etc)
```json
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

## Database
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

## File Operation
- Upload file
```json
HTTP: POST
URL: /api/v1/files/upload/path_of_file_name
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

- Download file
```json
HTTP: GET
URL: api/v1/files/download?path="path/of/file/file.name"
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

- Delete file or folder
```json
HTTP: POST
URL: /api/v1/files/delete
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: {"path": "path/of/delete/file/or/folder"}
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

- Move file or folder
```json
HTTP: POST
URL: /api/v1/files/move
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data:
    {
      "src_path": "path/of/src/folder/or/file",
      "dst_path": "path/of/dst/folder/or/file",
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

- Copy file or folder
```json
HTTP: POST
URL: /api/v1/files/copy
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data:
    {
      "src_path": "path/of/src/folder/or/file",
      "dst_path": "path/of/dst/folder/or/file",
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

- Get properties of file or folder
```json
HTTP: GET
URL: api/v1/files/properties?path="file.or.folder.name"
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
return:
    Success:
        {
            "_status": "OK",
            "type": file/folder,
            "name": "file_or_folder_name",
            "size": 230,
            "last_modify": 123012.2342,
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

- List folder
```json
HTTP: GET
URL: /api/v1/files/list/folder?name="folder.name"
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
return:
    Success:
        {
          "_status": "OK",
          "file_info_list":[
            {
              "type": file/folder,
              "name": "file_name",
              "size": 230
              "last_modify": 123012.2342,
            },
            {
              "type": folder,
              "name": "folder_name",
              "size": 230
              "last_modify": 123012.2342,
              },
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

- Get file hash(SHA256)
```
HTTP: GET
URL: /api/v1/files/file/hash?path="path/of/file/name/"
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
return:
    Success:
        {
          "_status": "OK",
<<<<<<< Updated upstream
          "SHA256": "3a29a81d7b2718a588a5f6f3491b3c57"
=======
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

## Scripting

### Register/Update a sub-condition on the backend. Sub conditions can be referenced from the client side, by the vault owner, while registering scripts using /scripting/set_script endpoint. This will insert/update a row in the collection "subconditions". If the name doesn't exist, it'll create a new row and if it does, it'll update the existing row.

- Create/Update a subcondition to check whether a user belongs in a particular group.
Note that on the query, the mapping "group_id": "id" represents that the client passes us a parameter called "group_id" and this is not the field name in the database. Rather, the field name on "groups" is actually "id" as represented by the mapping. This is to make it so that if there are multiple parameters with the same values, they can be passed just once thereby reducing duplication. Note that "*caller_did" is not passed but rather it's the DID of the user who's executing the script. This value will be retrieved automatically on the backend
```json
HTTP: POST
URL: /api/v1/scripting/set_subcondition
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data:
    {
      "name": "user_in_group",
      "condition": {
        "endpoint": "condition/has_results",
        "collection": "groups",
        "options": {
          "filter": {
            "group_id": "_id",
            "*caller_did": "friends"
          },
          "skip": 0,
          "limit": 10,
          "maxTimeMS": 1000000000
        }
      }
    }
return:
    Success:
        {
          "_status": "OK",
>>>>>>> Stashed changes
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

<<<<<<< Updated upstream
## Scripting
=======
- Create/Update a subcondition to check whether the group was created within the timeframe given on the query.
```json
HTTP: POST
URL: /api/v1/scripting/set_subcondition
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data:
    {
      "name": "group_created_age",
      "condition": {
        "endpoint": "condition/has_results",
        "collection": "groups",
        "options": {
          "filter": {
            "group_id": "_id",
            "group_created": "created"
          }
        }
      }
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
```
>>>>>>> Stashed changes

### Register a new script for a given app. This lets the vault owner register a script on his vault for a given app. The script is built on the client side, then serialized and stored on the hive back-end. Later on, anyone, including the vault owner or external users, can use /scripting/run_script endpoint to execute one of those scripts and get results/data. The same API is used to insert/update the scripts

- Create/Update a script that gets all the groups in an alphabetical ascending order that a particular DID user belongs to. There is no subcondition that needs to be satisfied for this script as everyone is able to retrieve other user's groups without any restriction.
Note: "*caller_did" is a reserved keyword that will automatically be replaced with the user DID on the backend
```json
HTTP: POST
URL: /api/v1/scripting/set_script
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data:
    {
      "name": "get_groups",
      "executable": {
        "type": "find",
        "name": "get_groups",
        "body": {
          "collection": "groups",
          "filter": {
            "*caller_did": "friends"
          },
          "options": {
            "projection": {
              "_id": false,
              "name": true
            }
          }
        }
      }
    }
return:
    Success:
        {
          "_status": "OK",
<<<<<<< Updated upstream
          "acknowledged": true,
          "matched_count": 0,
          "modified_count": 0,
          "upserted_id": "5f4aa0a116f409b032c1da0b"
=======
>>>>>>> Stashed changes
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

- Create/Update a script to get the first 100 messages for a particular group messaging. "_id" is not displays as part of the result. The condition first has to return successfully that checks whether the DID user belongs to the group. Then, the appropriate messages are returned back to the client.
In the executable, there's "group_id": "group_id". The key represents the value that's passed while run_script is called while the value represents the actual field name in the database. Please refer to the run_script example for more info.
Note: "*caller_did" is a reserved keyword that will automatically be replaced with the user DID on the backend
```json
HTTP: POST
URL: /api/v1/scripting/set_script
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data:
    {
      "name": "get_group_messages",
      "executable": {
        "type": "find",
        "name": "find_messages",
        "body": {
          "collection": "messages",
          "filter": {
            "group_id": "group_id"
          },
          "projection": {
            "_id": false,
          },
          "limit": 100
        }
      },
      "condition": {
        "type": "queryHasResults",
        "name": "verify_user_permission",
        "body": {
          "collection": "groups",
          "filter": {
            "group_id": "_id",
            "*caller_did": "friends"
          }
        }
      }
    }
return:
    Success:
        {
          "_status": "OK",
<<<<<<< Updated upstream
          "acknowledged": true,
          "matched_count": 0,
          "modified_count": 0,
          "upserted_id": "5f4aa1cf16f409b032c1dad2"
=======
>>>>>>> Stashed changes
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

- Create/Update a script to add a new message to the group messaging and then returns the last message in the group messaging that was just added. This script contains a condition of type "and" which means all the conditions defined have to return successfully first before the executables can be run.
Note: "*caller_did" is a reserved keyword that will automatically be replaced with the user DID on the backend
```json
HTTP: POST
URL: /api/v1/scripting/set_script
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data:
    {
      "name": "add_group_message",
      "executable": {
        "type": "aggregated",
        "name": "add_and_return_message",
        "body": [
          {
            "type": "insert",
            "name": "add_message_to_end",
            "body": {
              "collection": "messages",
              "document": {
                "group_id": "group_id",
                "*caller_did": "friend_did",
                "content": "content",
                "content_created": "created"
              },
              "options": {"bypass_document_validation": false}
            }
          },
          {
            "type": "find",
            "name": "get_last_message",
            "body": {
              "collection": "messages",
              "filter": {
                "group_id": "group_id"
              },
              "options": {
                "projection": {"_id": false},
                "sort": {"created": "desc"},
                "limit": 1
              }
            }
          }
        ]
      },
      "condition": {
        "type": "and",
        "name": "verify_user_permission",
        "body": [
          {
            "type": "queryHasResults",
            "name": "user_in_group",
            "body": {
              "collection": "groups",
              "filter": {
                "group_id": "_id",
                "*caller_did": "friends"
              }
            }
          },
          {
            "type": "queryHasResults",
            "name": "user_in_group",
            "body": {
              "collection": "groups",
              "filter": {
                "group_id": "_id",
                 "*caller_did": "friends"
              }
            }
          }
        ]
      }
    }
return:
<<<<<<< Updated upstream
    Success:
      {
        "_status": "OK",
        "acknowledged": true,
        "matched_count": 0,
        "modified_count": 0,
        "upserted_id": "5f4aa2be16f409b032c1daf4"
      }
    Failure:
=======
    Success:
        {
          "_status": "OK",
        }
    Failure:
>>>>>>> Stashed changes
        {
          "_status": "ERR",
          "_error": {
            "code": 401,
            "message": "Error message"
          }
        }
```

### Executes a previously registered server side script using /scripting/set_script endpoint. Vault owner or external users are allowed to call scripts on someone's vault

- Run a script to get all the groups that the DID user belongs to. As defined by the script, it contains no restriction so anyone is able to retrieve all the groups for a DID user
```json
HTTP: POST
URL: /api/v1/scripting/run_script
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data:
    {
      "name": "get_groups"
    }
return:
<<<<<<< Updated upstream
    Success:
      {
        "_status": "OK",
        "items": [
          {
            "name": "Tuum Tech"
          }
        ]
      }
    Failure:
=======
    Success:
        {
          "_status": "OK",
          "items": [
            {
              "name": "Group 1"
            },
            {
              "name": "Group 2"
            }
          ]
        }
    Failure:
>>>>>>> Stashed changes
        {
          "_status": "ERR",
          "_error": {
            "code": 401,
            "message": "Error message"
          }
        }
```

- Run a script to get all the group messages for a particular group ID. This has a subcondition that needs to be satisifed first. This subcondition can access the values of "params" as they are. Mongodb queries are allowed as part of these fields.
```json
HTTP: POST
URL: /api/v1/scripting/run_script
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data:
    {
      "name": "get_group_messages",
      "params": {
        "group_id": {"\$oid": "5f497bb83bd36ab235d82e6a"}
      }
    }
return:
    Success:
<<<<<<< Updated upstream
      {
        "_status": "OK",
        "items": [
          {
            "content": "Old Message",
            "created": {
              "$date": 1630022400000
=======
        {
          "_status": "OK",
          "_items": [
            {
              "created": "Wed, 25 Feb 1987 17:00:00 GMT",
              "content": "Old Message 1"
>>>>>>> Stashed changes
            },
            "friend_did": "did:elastos:ijUnD4KeRpeBUFmcEDCbhxMTJRzUYCQCZM",
            "group_id": {
              "$oid": "5f497bb83bd36ab235d82e6a"
            },
            "modified": {
              "$date": 1598725803556
            }
<<<<<<< Updated upstream
          }
        ]
      }
    Failure:
=======
          ]
        }
    Failure:
>>>>>>> Stashed changes
        {
          "_status": "ERR",
          "_error": {
            "code": 401,
            "message": "Error message"
          }
        }
```

- Run a script to add a new message to the group messaging for a particular group id. This has two subconditions that needs to be satisifed first. These subconditions can access the values of "params" as they are. Mongodb queries are allowed as part of these fields.
```json
HTTP: POST
URL: /api/v1/scripting/run_script
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data:
    {
      "name": "add_group_message",
      "params": {
        "group_id": "5f484a24efc1cbf6fc88ffb7",
        "group_created": {
          "$gte": "2021-08-27 00:00:00"
        },
        "content": "New Message",
        "content_created": "2021-08-27 00:00:00"
      }
    }
return:
    Success:
<<<<<<< Updated upstream
      {
        "_status": "OK",
        "items": [
          {
            "content": "New Message",
            "created": {
              "$date": 1630022400000
=======
        {
          "_status": "OK",
          "_items": [
            {
              "created": "Wed, 25 Feb 1987 17:00:00 GMT",
              "content": "Old Message 1"
>>>>>>> Stashed changes
            },
            "friend_did": "did:elastos:ijUnD4KeRpeBUFmcEDCbhxMTJRzUYCQCZM",
            "group_id": {
              "$oid": "5f497bb83bd36ab235d82e6a"
            },
            "modified": {
              "$date": 1598725803556
            }
<<<<<<< Updated upstream
          }
        ]
      }
    Failure:
=======
          ]
        }
    Failure:
>>>>>>> Stashed changes
        {
          "_status": "ERR",
          "_error": {
            "code": 401,
            "message": "Error message"
          }
        }
```
