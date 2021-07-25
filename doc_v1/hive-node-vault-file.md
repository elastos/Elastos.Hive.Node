# Vault File
## Upload file
```YAML
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
error code:
    (UNAUTHORIZED, "auth failed")
    (BAD_REQUEST, "vault does not exist.")
    (BAD_REQUEST, "vault have been freeze, can not write")
    (BAD_REQUEST, "not enough storage space")
    (NOT_FOUND, "file name is a directory")
    (INTERNAL_SERVER_ERROR, Exception message)
```

## Download file
```YAML
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
error code:
    UNAUTHORIZED
    FORBIDDEN
    INTERNAL_SERVER_ERROR
    NOT_FOUND
```

## Delete file or folder
```YAML
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
error code:
    (UNAUTHORIZED, "auth failed")
    (BAD_REQUEST, "vault does not exist.")
    (BAD_REQUEST, "vault have been freeze, can not write")
    (BAD_REQUEST, "parameter is not application/json") 
    (BAD_REQUEST, "parameter is null") 
    (INTERNAL_SERVER_ERROR, Exception message)
```

## Move file or folder
```YAML
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
error code:
    (UNAUTHORIZED, "auth failed")
    (BAD_REQUEST, "vault does not exist.")
    (BAD_REQUEST, "vault have been freeze, can not write")
    (BAD_REQUEST, "not enough storage space")
    (BAD_REQUEST, "parameter is not application/json") 
    (BAD_REQUEST, "parameter is null") 
    (NOT_FOUND, "src_name not exists")
    (METHOD_NOT_ALLOWED, "dst_name file exists")
    (INTERNAL_SERVER_ERROR, "make dst parent path dir error")
    (INTERNAL_SERVER_ERROR, exception message)
```

## Copy file or folder
```YAML
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
error code:
    (UNAUTHORIZED, "auth failed")
    (BAD_REQUEST, "vault does not exist.")
    (BAD_REQUEST, "vault have been freeze, can not write")
    (BAD_REQUEST, "not enough storage space")
    (BAD_REQUEST, "parameter is not application/json") 
    (BAD_REQUEST, "parameter is null") 
    (NOT_FOUND, "src_name not exists")
    (METHOD_NOT_ALLOWED, "dst_name file exists")
    (INTERNAL_SERVER_ERROR, "make dst parent path dir error")
    (INTERNAL_SERVER_ERROR, exception message)
```

## Get properties of file or folder
```YAML
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
error code:
    (UNAUTHORIZED, "auth failed")
    (BAD_REQUEST, "vault does not exist.")
    (BAD_REQUEST, "parameter is null") 
    (NOT_FOUND, "src_name not exists")
    (METHOD_NOT_ALLOWED, "file not exists")
    (INTERNAL_SERVER_ERROR, "make dst parent path dir error")
    (INTERNAL_SERVER_ERROR, exception message)
```

## List folder
```YAML
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
error code:
    (UNAUTHORIZED, "auth failed")
    (BAD_REQUEST, "vault does not exist.")
    (NOT_FOUND, "folder not exists")
```

## Get file hash(SHA256)
```YAML
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
error code:
    (UNAUTHORIZED, "auth failed")
    (BAD_REQUEST, "vault does not exist.")
    (BAD_REQUEST, "parameter is null") 
    (NOT_FOUND, "file not exists")
```

