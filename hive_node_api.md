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

## MongoDB operation
1. Setup mongoDB collection
```
HTTP: POST
URL: /api/v1/db/create_collection
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data:
    {
      "collection": "works",
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
          "collection": "works"
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

2. Use mongoDB collection
```
HTTP: POST GET PATCH DELETE
URL: api/v1/db/col/*
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data: defined by eve schema
return: defined by eve
comments: If you define a "collection" for mongoDB, You can CURD your collection item in mongoDB.
```
Detailed usage is in EVE document:
- [Features sub-resources](https://docs.python-eve.org/en/stable/features.html#sub-resources)
- [Features editing](https://docs.python-eve.org/en/stable/features.html#editing-a-document-patch)
- [Features soft-delete](https://docs.python-eve.org/en/stable/features.html#soft-delete)
- [Features filtering](https://docs.python-eve.org/en/stable/features.html#filtering)
- [Features sorting](https://docs.python-eve.org/en/stable/features.html#sorting)
- [Features pagination](https://docs.python-eve.org/en/stable/features.html#pagination)

Example:
1. Add data to works
```
HTTP: POST
URL: api/v1/db/col/works
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data:
    {
      "author": "john doe2",
      "title": "Eve for Dummies2"
    }
return:
    {
      "_updated": "Mon, 08 Jun 2020 06:29:10 GMT",
      "_created": "Mon, 08 Jun 2020 06:29:10 GMT",
      "_etag": "b6aa8f9d28a816a22c2d7a130c58255740f0f318",
      "_id": "5edddab688db87875fddc3a5",
      "_links": {
        "self": {
          "title": "Work",
          "href": "works/5edddab688db87875fddc3a5"
        }
      },
      "_status": "OK"
    }
```

2. Get all data of works
```
HTTP: GET
URL: api/v1/db/col/works
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
return:
    {
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