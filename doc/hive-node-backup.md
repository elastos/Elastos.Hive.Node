# Vault Backup

- Backup hive vault to google drive
```json
HTTP: POST
URL: /api/v1/backup/save/to/google_drive
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data:
    { 
        "token": "ya29.A0AfH6SMAuwGipoRVMVnvon_C_qqMhzpK53QzDQ8rapZavP_JXa8ASFecIKcKsy91oek8UvjbXfLMB9rlVG3Wj3X4e6drbNGuJjq97U8Lo6uwxwTpcmeybSl0wkQihwXZJlc3fKY31tvsT55vUbSSWwugPETCPZAFs2Oo_MURWbtY",
        "refresh_token": "1//06-2759fIGiJdCgYIARAAGAYSNwF-L9Irf7R8nimVqT2UieEcO5wtZMk1uNLxyBk_jB2WCPHDY7rhdTV_0WvHp5K09BWy1lUZnng",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "24235223939-guh47dijl0f0idm7h04bd44ulfcodta0.apps.googleusercontent.com",
        "client_secret": "mqaI40MlghlNkfaFtDBzvpGg",
        "scopes": ["https://www.googleapis.com/auth/drive"],
        "expiry": "2020-11-17T05:14:10Z"
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
comments: The input data is google oauth2 token to json, no need to change anything. There is a sample code in python: oauth_google_desktop.py
```

- Restore hive vault from google drive
```json
HTTP: POST
URL: /api/v1/backup/restore/from/google_drive
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data:
    { 
        "token": "ya29.A0AfH6SMAuwGipoRVMVnvon_C_qqMhzpK53QzDQ8rapZavP_JXa8ASFecIKcKsy91oek8UvjbXfLMB9rlVG3Wj3X4e6drbNGuJjq97U8Lo6uwxwTpcmeybSl0wkQihwXZJlc3fKY31tvsT55vUbSSWwugPETCPZAFs2Oo_MURWbtY",
        "refresh_token": "1//06-2759fIGiJdCgYIARAAGAYSNwF-L9Irf7R8nimVqT2UieEcO5wtZMk1uNLxyBk_jB2WCPHDY7rhdTV_0WvHp5K09BWy1lUZnng",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "24235223939-guh47dijl0f0idm7h04bd44ulfcodta0.apps.googleusercontent.com",
        "client_secret": "mqaI40MlghlNkfaFtDBzvpGg",
        "scopes": ["https://www.googleapis.com/auth/drive"],
        "expiry": "2020-11-17T05:14:10Z"
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
comments: The input data is google oauth2 token to json, no need to change anything. There is a sample code in python: oauth_google_desktop.py
```
