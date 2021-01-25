# Vault Backup

## Backup hive vault to google drive
```YAML
HTTP: POST
URL: /api/v1/backup/save_to_google_drive
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
comments: "The input data is google oauth2 token to json, no need to change anything. There is a sample code in python: oauth_google_desktop.py"
error code: 
    todo post json
    (UNAUTHORIZED, "auth failed")
    (BAD_REQUEST, "vault does not exist.")
    (BAD_REQUEST, "vault have been freeze, can not write")
    (BAD_REQUEST, "not enough storage space")
    (BAD_REQUEST, "parameter is not application/json")
    (BAD_REQUEST, "parameter is null")
```

## Restore hive vault from google drive
```YAML
HTTP: POST
URL: /api/v1/backup/restore_from_google_drive
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
comments: "The input data is google oauth2 token to json, no need to change anything. There is a sample code in python: oauth_google_desktop.py"
error code:
    (UNAUTHORIZED, "auth failed")
    (BAD_REQUEST, "vault does not exist.")
    (BAD_REQUEST, "vault have been freeze, can not write")
    (BAD_REQUEST, "not enough storage space")
    (BAD_REQUEST, "parameter is not application/json")
    (BAD_REQUEST, "parameter is null")
```

## Get backup state 
```YAML
HTTP: GET
URL: api/v1/backup/state
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
return:
    Success:
        {
            "_status": "OK",
            "hive_backup_state": "stop"// stop, backup, restore
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

## Backup hive vault to other hive node
```YAML
HTTP: POST
URL: /api/v1/backup/save_to_node
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data:
    { 
        "backup_credential": '{"id":"did:elastos:ijUnD4KeRpeBUFmcEDCbhxMTJRzUYCQCZM#didapp","type":["BackupCredential"],"issuer":"did:elastos:ij8krAVRJitZKJmcCufoLHQjq7Mef3ZjTN","issuanceDate":"2021-01-07T05:41:28Z","expirationDate":"2025-09-01T19:47:24Z","credentialSubject":{"id":"did:elastos:ijUnD4KeRpeBUFmcEDCbhxMTJRzUYCQCZM","sourceDID":"did:elastos:ijUnD4KeRpeBUFmcEDCbhxMTJRzUYCQCZM","targetDID":"did:elastos:ijUnD4KeRpeBUFmcEDCbhxMTJRzUYCQCZM","targetHost":"http://0.0.0.0:5000"},"proof":{"type":"ECDSAsecp256r1","verificationMethod":"did:elastos:ij8krAVRJitZKJmcCufoLHQjq7Mef3ZjTN#primary","signature":"1LfT8p5JGTQGhCpRnysBSsrZZS-Hctv_ejBn7fwaT649Manbiy6qMHvtla075x18xqqPIHB1ylWbVFBzfILUYA"}} '
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
comments: "backup_credential need to issue by user did, see it in hive_auth_test.py:issue_backup_auth"
error code:
    (UNAUTHORIZED, "auth failed") 
    (UNAUTHORIZED, "internal auth failed message") 
    (BAD_REQUEST, "vault does not exist.")
    (BAD_REQUEST, "vault have been freeze, can not write")
    (BAD_REQUEST, "not enough storage space")
    (BAD_REQUEST, "parameter is not application/json")
    (BAD_REQUEST, "parameter is null")
    (INSUFFICIENT_STORAGE, "The backup hive node dose not enough space for backup")
    (other code: hive interal communicate error )
```

## Restore hive vault from other hive node
```YAML
HTTP: POST
URL: /api/v1/backup/restore_from_node
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data:
    { 
        "backup_credential": '{"id":"did:elastos:ijUnD4KeRpeBUFmcEDCbhxMTJRzUYCQCZM#didapp","type":["BackupCredential"],"issuer":"did:elastos:ij8krAVRJitZKJmcCufoLHQjq7Mef3ZjTN","issuanceDate":"2021-01-07T05:41:28Z","expirationDate":"2025-09-01T19:47:24Z","credentialSubject":{"id":"did:elastos:ijUnD4KeRpeBUFmcEDCbhxMTJRzUYCQCZM","sourceDID":"did:elastos:ijUnD4KeRpeBUFmcEDCbhxMTJRzUYCQCZM","targetDID":"did:elastos:ijUnD4KeRpeBUFmcEDCbhxMTJRzUYCQCZM","targetHost":"http://0.0.0.0:5000"},"proof":{"type":"ECDSAsecp256r1","verificationMethod":"did:elastos:ij8krAVRJitZKJmcCufoLHQjq7Mef3ZjTN#primary","signature":"1LfT8p5JGTQGhCpRnysBSsrZZS-Hctv_ejBn7fwaT649Manbiy6qMHvtla075x18xqqPIHB1ylWbVFBzfILUYA"}} '
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
comments: "backup_credential need to issue by user did, see it in hive_auth_test.py:issue_backup_auth"
error code:
    (UNAUTHORIZED, "auth failed") 
    (UNAUTHORIZED, "internal auth failed message") 
    (BAD_REQUEST, "vault does not exist.")
    (BAD_REQUEST, "vault have been freeze, can not write")
    (BAD_REQUEST, "not enough storage space")
    (BAD_REQUEST, "parameter is not application/json")
    (BAD_REQUEST, "parameter is null")
    (BAD_REQUEST, "start node backup error")
    (INSUFFICIENT_STORAGE, "The backup hive node dose not enough space for backup")
    (other code: hive interal communicate error )
```

## Active hive backup data to vault
```YAML
HTTP: POST
URL: /api/v1/backup/activate_to_vault
Authorization: "token 38b8c2c1093dd0fec383a9d9ac940515"
Content-Type: "application/json"
data:
    {}
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
    (UNAUTHORIZED, "Backup backup_to_vault auth failed")
    (BAD_REQUEST, "There is not vault service of did to active")
    (BAD_REQUEST, "There is not vault backup service of did"
```
