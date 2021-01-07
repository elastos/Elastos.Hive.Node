# Scripting

### Register a new script for a given app. This lets the vault owner register a script on his vault for a given app. The script is built on the client side, then serialized and stored on the hive back-end. Later on, anyone, including the vault owner or external users, can use /scripting/run_script endpoint to execute one of those scripts and get results/data. The same API is used to insert/update the scripts

## Create/Update a script that gets all the groups in an alphabetical ascending order that a particular DID user belongs to. There is no subcondition that needs to be satisfied for this script as everyone is able to retrieve other user's groups without any restriction. 
Note: "$caller_did" is a reserved keyword that will automatically be replaced with the user DID on the backend. You may or may not add the param "output" as part of the executable whether to capture the output of each executable.
```YAML
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
        "output": true,
        "body": {
          "collection": "groups",
          "filter": {
            "friends": "$caller_did"
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
          "acknowledged": true,
          "matched_count": 0,
          "modified_count": 0,
          "upserted_id": "5f4aa0a116f409b032c1da0b"
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

## Create/Update a script to get the first 100 messages for a particular group messaging. "_id" is not displayed as part of the result. The condition first has to return successfully that checks whether the DID user belongs to the group. Then, the appropriate messages are returned back to the client.
Note: "$caller_did" is a reserved keyword that will automatically be replaced with the user DID on the backend and "$params" is a reserved keyword that will automatically fill the parameter value that's passed while calling the script. You may or may not add the param "output" as part of the executable whether to capture the output of each executable.
```YAML
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
        "output": true,
        "body": {
          "collection": "messages",
          "filter": {
            "group_id": "$params.group_id"
          },
          "projection": {
            "_id": false,
          },
          "limit": 100
        }
      },
      "condition": {
        "type": "queryHasResult",
        "name": "verify_user_permission",
        "body": {
          "collection": "groups",
          "filter": {
            "_id": "$params.group_id",
            "friends": "$caller_did"
          }
        }
      }
    }
return:
    Success: 
        {
          "_status": "OK",
          "acknowledged": true,
          "matched_count": 0,
          "modified_count": 0,
          "upserted_id": "5f4aa1cf16f409b032c1dad2"
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

## Create/Update a script to add a new message to the group messaging and then returns the last message in the group messaging that was just added. This script contains a condition of type "and" which means all the conditions defined have to return successfully first before the executables can be run. 
Note: "$caller_did" is a reserved keyword that will automatically be replaced with the user DID on the backend and "$params" is a reserved keyword that will automatically fill the parameter value that's passed while calling the script. You may or may not add the param "output" as part of the executable whether to capture the output of each executable.
```YAML
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
                "group_id": "$params.group_id",
                "friend_did": "$caller_did",
                "content": "$params.content",
                "created": "$params.content_created"
              },
              "options": {"bypass_document_validation": false}
            }
          },
          {
            "type": "find",
            "name": "get_last_message",
            "output": true,
            "body": {
              "collection": "messages",
              "filter": {
                "group_id": "$params.group_id"
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
            "type": "queryHasResult",
            "name": "user_in_group",
            "body": {
              "collection": "groups",
              "filter": {
                "_id": "$params.group_id",
                "friends": "$caller_did"
              }
            }
          },
          {
            "type": "queryHasResult",
            "name": "user_in_group",
            "body": {
              "collection": "groups",
              "filter": {
                "_id": "$params.group_id",
                "friends": "$caller_did"
              }
            }
          }
        ]
      }
    }
return:
    Success: 
        {
          "_status": "OK",
          "acknowledged": true,
          "matched_count": 0,
          "modified_count": 0,
          "upserted_id": "5f4aa2be16f409b032c1daf4"
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

## Create/Update a script(just for demoing delete and update query)
```YAML
HTTP: POST
URL: /api/v1/scripting/set_script
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: 
    {
      "name": "update_group_message_and_delete",
      "executable": {
        "type": "aggregated",
        "name": "update_and_delete",
        "body": [
          {
            "type": "update",
            "name": "update_and_return",
            "body": {
              "collection": "messages",
              "filter": {
                "group_id": "$params.group_id",
                "friend_did": "$caller_did",
                "content": "$params.old_content"
              },
              "update": {
                "$set": {
                  "group_id": "$params.group_id",
                  "friend_did": "$caller_did",
                  "content": "$params.new_content"
                }
              },
              "options": {
                "upsert": true,
                "bypass_document_validation": false
              }
            }
          },
          {
            "type": "delete",
            "name": "delete_and_return",
            "body": {
              "collection": "messages",
              "filter": {
                "group_id": "$params.group_id",
                "friend_did": "$caller_did",
                "content": "$params.content"
              }
            }
          }
        ]
      },
      "condition": {
        "type": "queryHasResults",
        "name": "verify_user_permission",
        "body": {
          "collection": "groups",
          "filter": {
            "_id": "$params.group_id",
            "friends": "$caller_did"
          }
        }
      }
    }
return:
    Success: 
        {
          "_status": "OK",
          "acknowledged": true,
          "matched_count": 0,
          "modified_count": 0,
          "upserted_id": "5f4aa2be16f409b032c1daf4"
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

## Upload a file(just for demoing fileUpload executable query). 
```YAML
HTTP: POST
URL: /api/v1/scripting/set_script
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: 
    {
      "name": "upload_picture",
      "executable": {
        "type": "fileUpload",
        "name": "upload_file",
        "output": true,
        "body": {
          "path": "$params.path"
        }
      },
      "condition": {
        "type": "queryHasResults",
        "name": "user_in_group",
        "body": {
          "collection": "groups",
          "filter": {
            "_id": "$params.group_id",
            "friends": "$caller_did"
          }
        }
      }
    }
return:
    Success: 
        {
          "_status": "OK",
          "acknowledged": true,
          "matched_count": 0,
          "modified_count": 0,
          "upserted_id": "5f4aa2be16f409b032c1daf4"
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


## Download a file(just for demoing fileDownload executable query)
```YAML
HTTP: POST
URL: /api/v1/scripting/set_script
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: 
    {
      "name": "download_picture",
      "executable": {
        "type": "fileDownload",
        "name": "download_file",
        "output": true,
        "body": {
          "path": "$params.path"
        }
      },
      "condition": {
        "type": "queryHasResults",
        "name": "user_in_group",
        "body": {
          "collection": "groups",
          "filter": {
            "_id": "$params.group_id",
            "friends": "$caller_did"
          }
        }
      }
    }
return:
    Success: 
        {
          "_status": "OK",
          "acknowledged": true,
          "matched_count": 0,
          "modified_count": 0,
          "upserted_id": "5f4aa2be16f409b032c1daf4"
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

## Get properties or a hash of a file(just for demoing purposes)
NOTE: We are going to allow anonymous access with this script by setting "allowAnonymousUser" to true and "allowAnonymousApp" to true
```YAML
HTTP: POST
URL: /api/v1/scripting/set_script
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: 
    {
      "name": "get_file_info",
      "allowAnonymousUser": true,
      "allowAnonymousApp": true,
      "executable": {
        "type": "aggregated",
        "name": "file_properties_and_hash",
        "body": [
          {
            "type": "fileProperties",
            "name": "file_properties",
            "output": true,
            "body": {
              "path": "$params.path"
            }
          },
          {
            "type": "fileHash",
            "name": "file_hash",
            "output": true,
            "body": {
              "path": "$params.path"
            }
          }
        ]
      }
    }
return:
    Success: 
        {
          "_status": "OK",
          "acknowledged": true,
          "matched_count": 0,
          "modified_count": 0,
          "upserted_id": "5f4aa2be16f409b032c1daf4"
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

## Run a script to get all the groups that the DID user belongs to. As defined by the script, it contains no restriction so anyone is able to retrieve all the groups for a DID user
```YAML
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
        "get_groups": {
          "items": [
            {
              "name": "Tuum Tech"
            }
          ]
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

## Run a script to get all the group messages for a particular group ID. This has a subcondition that needs to be satisifed first. This subcondition can access the values of "params" as they are. Mongodb queries are allowed as part of these fields.
NOTE: We can use the field "context" along with its inner value "target_did" to tell hive which did user to use when accessing vault and "target_app_did" to tell hive which app did to use when accessing vault. This is necessary when user1 wants to call user2's vault
```YAML
HTTP: POST
URL: /api/v1/scripting/run_script
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: 
    {
      "name": "get_group_messages",
      "context": {
        "target_did": "did:elastos:ij8krAVRJitZKJmcCufoLHQjq7Mef3ZjTN",
        "target_app_did": "appid"
      },
      "params": {
        "group_id": {"$oid": "5f497bb83bd36ab235d82e6a"}
      }
    }
return:
    Success:
      {
        "_status": "OK",
        "find_messages": {
          "items": [
            {
              "content": "Old Message",
              "created": {
                "$date": 1630022400000
              },
              "friend_did": "did:elastos:ijUnD4KeRpeBUFmcEDCbhxMTJRzUYCQCZM",
              "group_id": {
                "$oid": "5f497bb83bd36ab235d82e6a"
              },
              "modified": {
                "$date": 1598725803556
              }
            }
          ]
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

## Run a script to add a new message to the group messaging for a particular group id. This has two subconditions that needs to be satisifed first. These subconditions can access the values of "params" as they are. Mongodb queries are allowed as part of these fields.
```YAML
HTTP: POST
URL: /api/v1/scripting/run_script
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: 
    {
      "name": "add_group_message",
      "params": {
        "group_id": {"$oid": "5f497bb83bd36ab235d82e6a"},
        "group_created": {
          "$gte": "2021-08-27 00:00:00"
        },
        "content": "New Message",
        "content_created": "2021-08-27 00:00:00"
      }
    }
return:
    Success:
      {
        "_status": "OK",
        "get_last_message": {
          "items": [
            {
              "content": "New Message",
              "created": {
                "$date": 1630022400000
              },
              "friend_did": "did:elastos:ijUnD4KeRpeBUFmcEDCbhxMTJRzUYCQCZM",
              "group_id": {
                "$oid": "5f497bb83bd36ab235d82e6a"
              },
              "modified": {
                "$date": 1598725803556
              }
            }
          ]
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

## Run a script to upload a file
NOTE: The upload works a bit differently compared to other types of executable queries because there are two steps to this executable. First, you run the script to get a transaction ID and then secondly, you call a second API endpoint to actually upload the file related to that transaction ID
```YAML
HTTP: POST
URL: /api/v1/scripting/run_script
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: 
    {
      "name": "upload_file",
      "group_id": {"\$oid": "5fc46c9f3409d8a253dd8132"},
        "path": "logging.conf"
      }
    }
return:
    Success:
    {
      "_status": "OK",
      "upload_file": {
        "transaction_id": "5fc4b654d3ae60e2286f0ac0"
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
Then, run the second API endpoint to upload the file
```YAML
HTTP: POST
URL: /api/v1/scripting/run_script_upload/transaction_id
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

## Run a script to download a file
NOTE: The download works a bit differently compared to other types of executable queries because there are two steps to this executable. First, you run the script to get a transaction ID and then secondly, you call a second API endpoint to actually download the file related to that transaction ID
```YAML
HTTP: POST
URL: /api/v1/scripting/run_script
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: 
    {
      "name": "download_picture",
      "params": {
        "group_id": {"$oid": "5f497bb83bd36ab235d82e6a"},
        "path": "kiran.jpg"
      }
    }
return:
    Success:
    {
      "_status": "OK",
      "download_file": {
        "transaction_id": "5fc4b8ef740754a38ad9fd09"
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
Then, run the second API endpoint to download the file
```YAML
HTTP: POST
URL: /api/v1/scripting/run_script_download/transaction_id
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
data: file data
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

## Run a script to get properties and hash of a file
NOTE: This is a script where Anonymous options are set to true so we do not need to pass in an authorization token. 
  However, we MUST pass in the context with "target_did" and "target_app_did"
```YAML
HTTP: POST
URL: /api/v1/scripting/run_script
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: 
    {
      "name": "get_file_info",
      "context": {
        "target_did": "did:elastos:ij8krAVRJitZKJmcCufoLHQjq7Mef3ZjTN",
        "target_app_did": "did:elastos:jUdkrAVRJitZKJmcCufoLHQjq7Mef3Zi8L"
      },
      "params": {
        "path": "logging.conf"
      }
    }
return:
    Success: 
      {
        "_status": "OK",
        "file_hash": {
          "SHA256": "b032e73f4d677a82e932ba106b295365079d123973832c0fc1e06d3900e1fd84"
        },
        "file_properties": {
          "last_modify": 1602446791.5942733,
          "name": "logging.conf",
          "size": 78731,
          "type": "file"
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

