# Hive node plus plus api

## Table of Contents
- [Auth of did and app](#auth-of-did-and-app)
- [Synchronization](#synchronization)
- [Vault File](#vault-file)
- [Database](#database)
- [Scripting](#scripting)

## Auth of did and app
NOTE: There will be a new version
- User auth
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
- Init synchronization from google drive
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

## Vault File
- Create folder
```
HTTP: POST
URL: /api/v1/files/create_folder
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: 
  {
    "path": "path/of/folder/to/create"
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
```

- Upload file
```
HTTP: POST
URL: /api/v1/files/upload_file
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
data: local file path
folder_path: "path/of/folder/to/upload/the/file/to"
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
Example Request:
```
curl -X POST -F "data=@test.mp3" -F "folder_path=path/of/folder/to/upload/the/file/to" http://localhost:5000/api/v1/files/upload
```

- Download file
```
HTTP: GET
URL: /api/v1/files/download_file
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
data:
  {
    "path": "path/of/file/to/download"
  }
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

- Delete file/folder
```
HTTP: POST
URL: /api/v1/files/delete
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: 
  {
    "path": "path/of/file-folder/to/delete"
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
```

- Move file or folder
```
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
```
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

- Get file hash
```
HTTP: GET
URL: /api/v1/files/hash_file
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data:
  {
    "path": "path/of/file/to/get/hash/of"
    "type": "sha256"
  }
return:
    Success:
        {
          "_status": "OK",
          "hash": "3a29a81d7b2718a588a5f6f3491b3c57"
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
```
HTTP: GET
URL: /api/v1/files/list_folder
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data:
  {
    "path": "path/of/folder/to/get/the/files-list"
  }
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

- Get stat(properties) of file or folder
```
HTTP: GET
URL: api/v1/files/stat
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data:
  {
    "path": "path/of/file/to/get/properties/of"
  }
return:
    Success:
        {
          "_status": "OK",
          "_type": "file",
          "_created": 123012.2342,
          "_updated": 123012.2342,
          "_size": 230
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

## Database
- Create mongoDB collection
```
HTTP: POST
URL: /api/v1/db/create_collection
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: 
    {
      "name": "works",
      "schema": {
        "title": {
          "type": "string"
        },
        "author": {
          "type": "string"
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
comments: "collection" is collection name of user's mongoDB. schema definition is in EVE document: [Schema Definition](https://docs.python-eve.org/en/stable/config.html#schema-definition)
```

- Count documents
```
HTTP: POST
URL: /api/v1/db/count_documents
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: 
    {
      "name": "works",
      "query": {
        "title": "Eve for Dummies2"
      },
      "limit": 50,
      "skip": 10
    }
return:
    Success: 
        {
          "_status": "OK", 
          "count": 5
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
```
HTTP: POST
URL: /api/v1/db/find_one
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: 
    {
      "name": "works",
      "query": {
        "title": "Eve for Dummies2"
      },
      "limit": 50,
      "skip": 10,
      "sort": [
        ("title", -1)
      ],
      "projection": {
        "title": 1
      }
    }
return:
    Success: 
        {
          "_status": "OK", 
          "_id": "5ebb571d5e47c77fe2e4c184",
          "author": "john doe2",
          "title": "Eve for Dummies2",
          "_updated": "Wed, 13 May 2020 02:10:37 GMT",
          "_created": "Wed, 13 May 2020 02:10:37 GMT",
          "_etag": "6458561293d9ce4fcbb03d66df27d59ebc8bd611",
          "_links": {
            "self": {
              "title": "Work",
              "href": "works/5ebb571d5e47c77fe2e4c184"
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
```
HTTP: POST
URL: /api/v1/db/find_many
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: 
    {
      "name": "works",
      "query": {
        "title": "Eve for Dummies2"
      },
      "limit": 50,
      "skip": 10,
      "sort": [
        ("title", -1)
      ],
      "projection": {
        "title": 1
      }
    }
return:
    Success: 
        {
          "_status": "OK", 
          "_items": [
            {
              "_id": "5ebb571d5e47c77fe2e4c184",
              "author": "john doe2",
              "title": "Eve for Dummies2",
              "_updated": "Wed, 13 May 2020 02:10:37 GMT",
              "_created": "Wed, 13 May 2020 02:10:37 GMT",
              "_etag": "6458561293d9ce4fcbb03d66df27d59ebc8bd611",
              "_links": {
                "self": {
                  "title": "Work",
                  "href": "works/5ebb571d5e47c77fe2e4c184"
                }
              }
            }
          ],
          "_links": {
            "parent": {
              "title": "home",
              "href": "/"
            },
            "self": {
              "title": "works",
              "href": "works"
            }
          },
          "_meta": {
            "page": 1,
            "max_results": 25,
            "total": 1
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

- Insert a new document in a given collection
```
HTTP: POST
URL: /api/v1/db/insert_one
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: 
    {
      "name": "works",
      "document": {
        "author": "john doe1", 
        "title": "Eve for Dummies2"
      }
    }
return:
    {
      "_status": "OK",
      "count": 1,
      "ids": [
        "5edddab688db87875fddc3a5"
      ]
    }
```

- Insert many new documents in a given collection
```
HTTP: POST
URL: /api/v1/db/insert_many
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: 
    {
      "name": "works",
      "document": [
        {
          "author": "john doe1", 
          "title": "Eve for Dummies1"
        },
        {
          "author": "john doe2", 
          "title": "Eve for Dummies2"
        }
      ]
    }
return:
    {
      "_status": "OK",
      "count": 2,
      "ids": [
        "5edddab688db87875fddc3a5",
        "6eddbab688db12r46Fr036b7"
      ]
    }
```

- Update an existing document in a given collection
```
HTTP: POST
URL: /api/v1/db/update_one
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: 
    {
      "name": "works",
      "document": {
        "_id": "5edddab688db87875fddc3a5",
        "author": "john doe3", 
        "title": "Eve for Dummies2"
      }
    }
return:
    {
      "_status": "OK",
      "count": 1
    }
```

- Update many existing documents in a given collection
```
HTTP: POST
URL: /api/v1/db/update_many
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: 
    {
      "name": "works",
      "document": [
        {
          "_id": "5edddab688db87875fddc3a5",
          "author": "john doe5", 
          "title": "Eve for Dummies5"
        },
        {
          "_id": "6eddbab688db12r46Fr036b7",
          "author": "john doe6", 
          "title": "Eve for Dummies6"
        }
      ]
    }
return:
    {
      "_status": "OK",
      "count": 2
    }
```

- Delete an existing document in a given collection
```
HTTP: POST
URL: /api/v1/db/delete_one
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: 
    {
      "name": "works",
      "document": {
        "_id": "5edddab688db87875fddc3a5"
      }
    }
return:
    {
      "_status": "OK",
      "count": 1
    }
```

- Delete many existing documents in a given collection
```
HTTP: POST
URL: /api/v1/db/delete_many
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: 
    {
      "name": "works",
      "document": [
        {
          "_id": "5edddab688db87875fddc3a5"
        },
        {
          "_id": "6eddbab688db12r46Fr036b7"
        }
      ]
    }
return:
    {
      "_status": "OK",
      "count": 2
    }
```  




## Scripting
- Register a sub-condition on the backend. Sub conditions can be referenced from the client side, by the vault owner, while registering scripts using /scripting/set_script endpoint
```
HTTP: POST
URL: /api/v1/scripting/register_subcondition
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: 
    {
      "name": "works",
      "condition": {
        "TODO"
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

- Register a new script for a given app. This lets the vault owner register a script on his vault for a given app. The script is built on the client side, then serialized and stored on the hive back-end. Later on, anyone, including the vault owner or external users, can use /scripting/call endpoint to execute one of those scripts and get results/data
```
HTTP: POST
URL: /api/v1/scripting/set_script
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: 
    {
      "name": "function_name",
      "sequence": [
        "TODO"
      ]
      "condition": {
        "TODO"
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

- Executes a previously registered server side script using /scripting/set_script endpoint. Vault owner or external users are allowed to call scripts on someone's vault
```
HTTP: POST
URL: /api/v1/scripting/call_script
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: 
    {
      "name": "function_name",
      "params": {
        "TODO"
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