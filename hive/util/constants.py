from decouple import config

DID_INFO_DB_NAME = config('DID_INFO_DB_NAME', default="hive_manage_info", cast=str)

DID_INFO_REGISTER_COL = "auth_register"
DID = "did"
APP_ID = "app_id"
DID_INFO_NONCE = "nonce"
DID_INFO_TOKEN = "token"
DID_INFO_NONCE_EXPIRE = "nonce_expire"
DID_INFO_TOKEN_EXPIRE = "token_expire"

DID_SYNC_INFO_COL = "did_sync_info"
DID_SYNC_INFO_STATE = "state"
DID_SYNC_INFO_MSG = "msg"
DID_SYNC_INFO_TIME = "time"
DID_SYNC_INFO_DRIVE = "drive"

DID_RESOURCE_COL = "user_db_col_schema"
DID_RESOURCE_DID = "did"
DID_RESOURCE_APP_ID = "app_id"
DID_RESOURCE_NAME = "name"
DID_RESOURCE_SCHEMA = "schema"

FILE_INFO_COL = "file_data"
FILE_INFO_BELONG_DID = "belong_did"
FILE_INFO_BELONG_APP_ID = "belong_app_id"
FILE_INFO_FILE_NAME = "file_name"
FILE_INFO_FILE_SIZE = "file_size"
FILE_INFO_FILE_CREATE_TIME = "file_create_time"
FILE_INFO_FILE_MODIFY_TIME = "file_modify_time"
# db of file_info end

DID_AUTH_SUBJECT = "didauth"
DID_AUTH_REALM = "elastos_hive_node"

SCRIPTING_DID = "did"
SCRIPTING_APP_ID = "app_id"
SCRIPTING_NAME = "name"
SCRIPTING_SUBCONDITION_COLLECTION = "subconditions"
SCRIPTING_SCRIPT_COLLECTION = "scripts"
SCRIPTING_CONDITION = "condition"
SCRIPTING_CONDITION_TYPE = "condition_type"
SCRIPTING_EXEC_SEQUENCE = "exec_sequence"
SCRIPTING_EXECUTABLE_FIND_ONE = "db/find_one"
SCRIPTING_EXECUTABLE_FIND_MANY = "db/find_many"
SCRIPTING_EXECUTABLE_INSERT_ONE = "db/insert_one"
SCRIPTING_EXECUTABLE_UPDATE_MANY = "db/update_many"
SCRIPTING_EXECUTABLE_DELETE_MANY = "db/delete_many"
SCRIPTING_EXECUTABLE_CALLER_DID = "*caller_did"
SCRIPTING_SUBCONDITIONS_SCHEMA = {
    "collection": "subconditions",
    "schema": {
        "id": {
            "type": "string"
        },
        "name": {
            "type": "string"
        },
        "did": {
            "type": "string"
        },
        "app_id": {
            "type": "string"
        },
        "condition_type": {
            "type": "string"
        },
        "condition": {
            "type": "dict"
        }
    }
}
SCRIPTING_SCRIPTS_SCHEMA = {
    "collection": "scripts",
    "schema": {
        "id": {
            "type": "string"
        },
        "name": {
            "type": "string"
        },
        "did": {
            "type": "string"
        },
        "app_id": {
            "type": "string"
        },
        "exec_sequence": {
            "type": "dict"
        },
        "condition": {
            "type": "dict",
            "schema": {
                "operation": {
                    "type": "string"
                },
                "name": {
                    "type": "string"
                }
            }
        }
    }
}