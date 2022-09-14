Backup Protocol between Vault and Backup Node
=============================================

## Request Metadata

```json
{
    "version": "1.0",
    "databases": [{
        "name": "<database name>",
        "sha256": "<sha256 of dump file>",
        "cid": "<cid in the vault node>",
        "size": "<size of the dump file>"
    }],
    "files": [{
        "sha256": "<sha256 of the file content>",
        "cid": "<cid in the vault node>",
        "size": "<size of the file>",
        "count": "<reference count of the cid.>"
    }],
    "user_did": "<user did>",
    "vault_size": "<the size of the user's vault.>",
    "vault_package_size": "<the database dump file and user files size.>",
    "create_time": "<create time of this request metadata.>",
    "encryption": {
        "secret_key": "<base58 of the private key to encrypt the database files>",
        "nonce": "<base58 of the private key to encrypt the database files>"
    }
}
```

## Internal API

### State

```
GET /vault-backup-service/state (URL_SERVER_INTERNAL_STATE)

Request Body:
    None
    
Response Body:
    {
        "state": <action>,
        "result": <state>,
        "message": <error message>,
        "public_key": <public key for encryption>
    }
```

### Backup

```
POST /vault-backup-service/backup (URL_SERVER_INTERNAL_BACKUP)

Request Body:
    {
        "cid": <cid of the backup metadata>,
        "sha256": <sha256 of the backup metadata>,
        "size": <the size of the backup metadata>,
        "is_force": <whether force backup or restore>,
        "public_key": <public key for curve25519>
    }
    
Response Body:
    None
```

### Restore

```
GET /vault-backup-service/restore (URL_SERVER_INTERNAL_RESTORE)

URL Parameters:
    public_key=<public key>

Request Body:
    None
    
Response Body:
    {
        "cid": <cid of the backup metadata>,
        "sha256": <sha256 of the backup metadata>,
        "size": <the size of the backup metadata>,
        "public_key": <public key for curve25519>
    }
```