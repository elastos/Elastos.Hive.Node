# Hive node plus plus api

1. User register
    HTTP: POST
    URL : /api/v1/did/register
    Content-Type: "application/json"
    data: {"did":"iUWjzkS4Di75yCXiKJqxrHYxQdBcS2NaPk", "password":"adujejd"}
    return: 
        成功:{"_status":"OK"} 
        失败:{"_status": "ERR", "_error": {"code": 401, "message": "Error message"}}
        
1. User login 
    HTTP: POST
    URL : /api/v1/did/login
    Content-Type: "application/json"
    data: {"did":"iUWjzkS4Di75yCXiKJqxrHYxQdBcS2NaPk", "password":"adujejd"}
    return: 
        成功:{"_status":"OK", "token":"38b8c2c1093dd0fec383a9d9ac940515"}
        失败:{"_status": "ERR", "_error": {"code": 401, "message": "Error message"}}
        
1. Setup mongodb collection
    HTTP: POST
    URL : api/v1/db/create_collection
    Authorization:"token 38b8c2c1093dd0fec383a9d9ac940515"
    Content-Type: "application/json"
    data: { "collection":"works",
            "schema": {"title": {"type": "string"}, "author": {"type": "string"}}
          }
    return: 
        成功:{"_status":"OK", "collection":"works"}
        失败:{"_status": "ERR", "_error": {"code": 401, "message": "Error message"}}
    comments: "collection" is collection name of mongodb. schema definition is in EVE document: [Schema Definition](https://docs.python-eve.org/en/stable/config.html#schema-definition)

1. use mongodb collection
    HTTP: POST GET PATCH DELETE
    URL : api/v1/db/col/*
    Authorization:"token 38b8c2c1093dd0fec383a9d9ac940515"
    Content-Type: "application/json"
    data: defined by eve schema
    return: defined by eve
    comments: If you define a "collection" for mongodb, You can CURD your collection item in mongodb. 
    detailed usage is in EVE document: 
    [Features sub-resources](https://docs.python-eve.org/en/stable/features.html#sub-resources)
    [Features editing](https://docs.python-eve.org/en/stable/features.html#editing-a-document-patch)
    [Features soft-delete](https://docs.python-eve.org/en/stable/features.html#soft-delete)
    [Features filtering](https://docs.python-eve.org/en/stable/features.html#filtering)
    [Features sorting](https://docs.python-eve.org/en/stable/features.html#sorting)
    [Features pagination](https://docs.python-eve.org/en/stable/features.html#pagination)
    example:
        ```
            1. Add data to works
            HTTP: POST
            URL : api/v1/db/col/works
            Authorization:"token 38b8c2c1093dd0fec383a9d9ac940515"
            Content-Type: "application/json"
            data: {"author": "john doe2", "title": "Eve for Dummies2"}
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
            2. Get all data of works
            HTTP: GET
            URL : api/v1/db/col/works
            Authorization:"token 38b8c2c1093dd0fec383a9d9ac940515"
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
 
1. file upload 
    HTTP: POST
    URL : api/v1/file/uploader
    Authorization:"token 38b8c2c1093dd0fec383a9d9ac940515"
    Content-Type: "multipart/form-data"
    data: file="path/of/file/name" 
    return: 
        成功:{"_status":"OK"}
        失败:{"_status": "ERR", "_error": {"code": 401, "message": "Error message"}}

1. file list 
    HTTP: GET 
    URL : api/v1/file/list
    Authorization:"token 38b8c2c1093dd0fec383a9d9ac940515"
    Content-Type: "application/json"
    return: 
        成功:
        {
            "_status": "OK",
            "files": [
                "test.png"
            ]
        }
        失败:{"_status": "ERR", "_error": {"code": 401, "message": "Error message"}}
    
1. file download
    HTTP: GET 
    URL : api/v1/file/downloader?filename="file.name"
    Authorization:"token 38b8c2c1093dd0fec383a9d9ac940515"
    Content-Type: "application/json"
    return: 
        成功:
        {
            "_status": "OK",
            "files": [
                "test.png"
            ]
        }
        失败:{"_status": "ERR", "_error": {"code": 401, "message": "Error message"}}
        
1. get file info 
    HTTP: GET 
    URL : api/v1/file/info?filename="file.name"
    Authorization:"token 38b8c2c1093dd0fec383a9d9ac940515"
    Content-Type: "application/json"
    return: 
        成功:
        {
            "_status": "OK",
            "file": "test.png"
            "size": 123012 
        }
        失败:{"_status": "ERR", "_error": {"code": 401, "message": "Error message"}}
    
1. file delete 
    HTTP: POST
    URL : api/v1/file/delete
    Authorization:"token 38b8c2c1093dd0fec383a9d9ac940515"
    Content-Type: "multipart/form-data"
    data: {"file_name": "test.png"}
    return: 
        成功:{"_status":"OK"}
        失败:{"_status": "ERR", "_error": {"code": 401, "message": "Error message"}}

