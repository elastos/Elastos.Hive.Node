# Service manage

## create free vault service
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
error code:
    (UNAUTHORIZED, "auth failed")
comment: if vault exist, it will return
      {
        "_status": "OK",
        "existing": True
      }

```

## remove vault service
```YAML
HTTP: POST
URL: /api/v1/service/vault/remove
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
error code:
    (UNAUTHORIZED, "auth failed")
```

## freeze vault service
```YAML
HTTP: POST
URL: /api/v1/service/vault/freeze 
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
error code:
    (UNAUTHORIZED, "auth failed")
```

## unfreeze vault service
```YAML
HTTP: POST
URL: /api/v1/service/vault/unfreeze 
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
error code:
    (UNAUTHORIZED, "auth failed")
```

## Get vault service info 
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
                "did": "did:elastos:ij8krAVRJitZKJmcCufoLHQjq7Mef3ZjTN",
                "max_storage": 500, // Max 500 Mb storage size
                "file_use_storage": 100, // user have used 100 Mb in file storage size
                "db_use_storage": 50, // user have used 100 Mb in db storage size
                "modify_time": 1602236316,
                "start_time": 1602236316,
                "end_time": 1604914928,
                "pricing_using": "Rookie", // vault plan
                "state": "running" // running, freeze
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
error code:
    (UNAUTHORIZED, "auth failed")
    (NOT_FOUND, "vault service not found")
```

## create free backup vault service
```YAML
HTTP: POST
URL: /api/v1/service/vault_backup/create
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
error code:
    (UNAUTHORIZED, "auth failed")
comment: if vault exist, it will return
      {
        "_status": "OK",
        "existing": True
      }
```

## Get backup vault service info 
```YAML
HTTP: GET
URL: /api/v1/service/vault_backup
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
return:
    Success:
        {
            "_status": "OK",
            "vault_service_info":
            { 
                "did": "did:elastos:ij8krAVRJitZKJmcCufoLHQjq7Mef3ZjTN",
                "backup_using": "Rookie",// backup plan
                "max_storage": 500, // Max 500 Mb backup storage size
                "use_storage": 10, // have used 100 Mb backup storage size
                "modify_time": 1602236316,
                "start_time": 1602236316,
                "end_time": 1604914928,
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
error code:
    (UNAUTHORIZED, "auth failed")
    (NOT_FOUND, "vault backup service not found")
```



