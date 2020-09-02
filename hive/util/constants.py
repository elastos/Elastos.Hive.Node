from decouple import config

DID_INFO_DB_NAME = config('DID_INFO_DB_NAME', default="hive_manage_info", cast=str)

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

DID_INFO_REGISTER_COL = "auth_register"
DID = "did"
APP_ID = "app_id"
APP_INSTANCE_DID = "app_instance_did"
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

SCRIPTING_NAME = "name"
SCRIPTING_CONDITION_COLLECTION = "conditions"
SCRIPTING_SCRIPT_COLLECTION = "scripts"
SCRIPTING_CONDITION_TYPE_QUERY_HAS_RESULTS = "queryHasResult"
SCRIPTING_CONDITION_TYPE_AND = "and"
SCRIPTING_CONDITION_TYPE_OR = "or"
SCRIPTING_EXECUTABLE_TYPE_AGGREGATED = "aggregated"
SCRIPTING_EXECUTABLE_TYPE_FIND = "find"
SCRIPTING_EXECUTABLE_TYPE_INSERT = "insert"

SCRIPTING_EXECUTABLE_CALLER_DID = "*caller_did"
