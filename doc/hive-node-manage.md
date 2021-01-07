# Hive node manage
- Get hive node version
```YAML
HTTP: GET
URL: /api/v1/hive/version
return:
    Success:
        {
            "_status": "OK",
            "version": "1.0.0"
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

- Get commit hash 
```YAML
HTTP: GET
URL: /api/v1/hive/commithash
return:
    Success:
        {
            "_status": "OK",
            "commit_hash": "279b15650a86b16dcba289e74a09290ff225c69a"
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
