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
```json
HTTP: POST
URL: /api/v1/did/auth
Content-Type: "application/json"
data: {"jwt": "auth_token"}
return:
    Success:
        {
          "_status":"OK",
          "subject": "didauth",
          "issuer": "elastos_hive_node",
          "token": "access_token"
        }
    Failure: 
        {
          "_status": "ERR",
          "_error": {
            "code": 401,
            "message": "err_message"
          }
        }
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

## Vault File
- Create folder
```json
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
```json
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
```json
curl -X POST -F "data=@test.mp3" -F "folder_path=path/of/folder/to/upload/the/file/to" http://localhost:5000/api/v1/files/upload
```

- Download file
```json
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
```json
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

- Get file hash
```json
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
```json
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
```json
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
          "type": "file",
          "created": "Wed, 13 May 2020 02:10:37 GMT",
          "modified": "Wed, 13 May 2020 02:10:37 GMT",
          "size": 230
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
```json
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
```json
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
      "options": {
        "limit": 50,
        "skip": 10
      }
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
```json
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
      "options": {
        "limit": 50,
        "skip": 10,
        "sort": [
          "-title"
        ],
        "projection": {
          "title": 1
        }
      }
    }
return:
    Success: 
        {
          "_status": "OK", 
          "_id": "5ebb571d5e47c77fe2e4c184",
          "author": "john doe2",
          "title": "Eve for Dummies2",
          "modified": "Wed, 13 May 2020 02:10:37 GMT",
          "created": "Wed, 13 May 2020 02:10:37 GMT"
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
```json
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
      "options": {
        "limit": 50,
        "skip": 10,
        "sort": [
          "title"
        ],
        "projection": {
          "title": 1
        }
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
              "created": "Wed, 13 May 2020 02:10:37 GMT",
              "modified": "Wed, 13 May 2020 02:10:37 GMT"
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

- Insert a new document in a given collection
```json
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
      },
      "options": {}
    }
return:
    Success:
        {
          "_status": "OK",
          "count": 1,
          "ids": [
            "5edddab688db87875fddc3a5"
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

- Insert many new documents in a given collection
```json
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
      ],
      "options": {}
    }
return:
    Success:
        {
          "_status": "OK",
          "count": 2,
          "ids": [
            "5edddab688db87875fddc3a5",
            "6eddbab688db12r46Fr036b7"
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
```json
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
      },
      "options": {}
    }
return:
    Success:
        {
          "_status": "OK",
          "count": 1
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
```json
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
      ],
      "options": {}
    }
return:
    Success:
        {
          "_status": "OK",
          "count": 2
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
```json
HTTP: POST
URL: /api/v1/db/delete_one
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: 
    {
      "name": "works",
      "document": {
        "_id": "5edddab688db87875fddc3a5"
      },
      "options": {}
    }
return:
    Success:
        {
          "_status": "OK",
          "count": 1
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
```json
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
      ],
      "options": {}
    }
return:
    Success:
        {
          "_status": "OK",
          "count": 2
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
Note that on the query, the mapping "group_id": "id" represents that the client passes us a parameter called "group_id" and this is not the field name in the database. Rather, the field name on "groups" is actually "id" as represented by the mapping. This is to make it so that if there are multiple parameters with the same values, they can be passed just once thereby reducing duplication.
```json
HTTP: POST
URL: /api/v1/scripting/set_subcondition
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: 
    {
      "name": "user_in_group",
      "condition": {
        "collection": "groups",
        "query": {
          "group_id": "id", 
          "friend_did": "friends"
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
- Create/Update a subcondition to check whether the group was created within the timeframe given on the query
```json
HTTP: POST
URL: /api/v1/scripting/set_subcondition
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: 
    {
      "name": "group_created_age",
      "condition": {
        "collection": "groups",
        "query": {
          "group_id": "id", 
          "group_created": "created"
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

### Register a new script for a given app. This lets the vault owner register a script on his vault for a given app. The script is built on the client side, then serialized and stored on the hive back-end. Later on, anyone, including the vault owner or external users, can use /scripting/run_script endpoint to execute one of those scripts and get results/data

- Create/Update a script that gets all the groups in an alphabetical ascending order that a particular DID user belongs to. There is no subcondition that needs to be satisfied for this script as everyone is able to retrieve other user's groups without any restriction.
```json
HTTP: POST
URL: /api/v1/scripting/set_script
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: 
    {
      "name": "get_groups",
      "app_id": "tech.tuum.academy",
      "exec_sequence": [
        {
          "type": "db/find_many",
          "name": "groups",
          "query": {
            "did": "did:elastos:iUhndsxcgijret834Hdasdf31Ld"
          },
          "options": {
            "sort": [
              "name"
            ],
            "projection": {
              "id": 1,
              "name": 1
            }
          }
        }
      ]
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

- Create/Update a script to get messages for a particular group messaging in an ascending order according to the modified time. This script further skins the first 10 messages from the group and only gets 50 total messages after that point. Only the messages and modified time are returned back to the user. The condition first has to return successfully that checks whether the DID user belongs to the group. Then, the appropriate messages with their last modified date are returned back to the client.
```json
HTTP: POST
URL: /api/v1/scripting/set_script
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: 
    {
      "name": "get_group_messages",
      "app_id": "tech.tuum.academy",
      "exec_sequence": [
        {
          "endpoint": "db/find_many",
          "name": "messages",
          "query": {
            "group_id": "4aktrab688db87875fddc6Km"
          },
          "options": {
            "limit": 50,
            "skip": 10,
            "sort": [
              "modified"
            ],
            "projection": {
              "modified": 1,
              "content": 1
            }
          }
        }
      ],
      "condition": "user_in_group"
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

- Create/Update a script to add a new message to the group messaging and then returns all the messages in the group messaging including the newly added one sorted by their modification time. This script contains a condition with "$and" expression. This means that all the subconditions have to return true before the script is executed. First condition is to check whether the DID user belongs to the group and the second condition is to check whether the group was created withint within the given timeframe(passed with parameter in scripting/run_script)
```json
HTTP: POST
URL: /api/v1/scripting/set_script
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: 
    {
      "name": "add_group_message",
      "app_id": "tech.tuum.academy",
      "exec_sequence": [
        {
          "endpoint": "db/insert_one"
          "name": "messages",
          "document": {
            "group_id": "4aktrab688db87875fddc6Km", 
            "friend_did": "did:elastos:iUhndsxcgijret834Hdasdf31Ld",
            "content": "New message"
          },
          "options": {}
        },
        {
          "endpoint": "db/find_many"
          "name": "messages",
          "query": {
            "group_id": "4aktrab688db87875fddc6Km"
          },
          "options": {
            "sort": [
              "modified"
            ],
            "projection": {
              "modified": 1,
              "content": 1
            }
          }
        }
      ]
      "condition": {
        "$and": [
          "user_in_group",
          "group_created_age"
        ]
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
    Success: 
        {
          "_status": "OK", 
          "_items": [
            {
              "_id": "4aktrab688db87875fddc6Km",
              "name": "Group 1"
            },
            {
              "_id": "5akttab688db87875nddc6Ka",
              "name": "Group 2"
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
        "group_id": "4aktrab688db87875fddc6Km",
        "friend_did": {
          "$in": ["did:elastos:iUhndsxcgijret834Hdasdf31Ld"]
        }
      }
    }
return:
    Success:
        {
          "_status": "OK", 
          "_items": [
            {
              "_id": "7akkrab688db87875fddc6Kp",
              "content": "Old Message 1"
            },
            {
              "_id": "46kttab688db87875nddc6Ky",
              "content": "Old Message 2"
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
        "group_id": "4aktrab688db87875fddc6Km",
        "friend_id": "did:elastos:iUhndsxcgijret834Hdasdf31Ld"
        "group_created": {
          "$gte": "Wed, 25 Feb 1987 17:00:00 GMT"
        }
      }
    }
return:
    Success:
        {
          "_status": "OK", 
          "_items": [
            {
              "_id": "7akkrab688db87875fddc6Kp",
              "content": "Old Message 1"
            },
            {
              "_id": "46kttab688db87875nddc6Ky",
              "content": "Old Message 2"
            },
            {
              "_id": "38kttab688db87875nddc6yn",
              "content": "New message"
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
