# Hive node plus plus api

1. User register
    HTTP: POST
    URL : /api/v1/hivenode/user/register
    data: {"did":"iUWjzkS4Di75yCXiKJqxrHYxQdBcS2NaPk", "password":"adujejd"}
    return: 
        成功:{"_status":"OK"} 
        失败:{"_status": "ERR", "_error": {"code": 401, "message": "Error message"}}
        
1. User login 
    HTTP: POST
    URL : /api/v1/hivenode/user/login
    data: {"did":"iUWjzkS4Di75yCXiKJqxrHYxQdBcS2NaPk", "password":"adujejd"}
    return: 
        成功:{"_status":"OK", "token":"38b8c2c1093dd0fec383a9d9ac940515"}
        失败:{"_status": "ERR", "_error": {"code": 401, "message": "Error message"}}
        
1. Setup collection
    HTTP: POST
    URL : /api/v1/hivenode/collection
    Header—Authorization:"token 38b8c2c1093dd0fec383a9d9ac940515"
    data: { "collection":"works",
            "schema": {"title": {"type": "string"}, "author": {"type": "string"}}
          }
    return: 
        成功:{"_status":"OK", "collection":"works"}
        失败:{"_status": "ERR", "_error": {"code": 401, "message": "Error message"}}
