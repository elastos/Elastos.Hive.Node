# Service manage

## create vault service by free pricing
```YAML
HTTP: POST
URL: /api/v1/service/vault/create
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
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

## Get user vault service info 
```YAML
HTTP: GET
URL: api/v1/service/vault
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
return:
    Success:
        {
            "_status": "OK",
            "vault_service_info":
            { 
                "max_storage": 500, // Max 500 Mb storage size
                "file_use_storage": 100, // user have used 100 Mb in file storage size
                "db_use_storage": 50, // user have used 100 Mb in db storage size
                "modify_time": 1602236316,
                "start_time": 1602236316,
                "end_time": 1604914928,
                "pricing_using": "Rookie",// Free, Rookie, Advanced
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


