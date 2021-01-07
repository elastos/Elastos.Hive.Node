# Vault File
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
URL: /api/v1/files/download?path="path/of/file/file.name"
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
URL: /api/v1/files/list/folder?path="folder.name"
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
```json
HTTP: GET
URL: /api/v1/files/file/hash?path="path/of/file/name/"
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
return:
    Success:
        {
          "_status": "OK",
          "SHA256": "3a29a81d7b2718a588a5f6f3491b3c578a5f6f3491b3c578a5f6f3491b3c578a5f6f3491b3c57"
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

