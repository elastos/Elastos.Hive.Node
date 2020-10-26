from decouple import config

DID_INFO_DB_NAME = config('DID_INFO_DB_NAME', default="hive_manage_info", cast=str)

VAULT_ACCESS_WR = "vault_write_read"
VAULT_ACCESS_R = "vault_read"

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

DID_INFO_REGISTER_COL = "auth_register"
DID = "did"
APP_ID = "app_id"
APP_INSTANCE_DID = "app_instance_did"
DID_INFO_NONCE = "nonce"
DID_INFO_TOKEN = "token"
DID_INFO_NONCE_EXPIRED = "nonce_expired"
DID_INFO_TOKEN_EXPIRED = "token_expired"

DID_SYNC_INFO_COL = "did_sync_info"
DID_SYNC_INFO_STATE = "state"
DID_SYNC_INFO_MSG = "msg"
DID_SYNC_INFO_TIME = "time"
DID_SYNC_INFO_DRIVE = "drive"

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

# scripting begin
SCRIPTING_NAME = "name"
SCRIPTING_CONDITION_COLLECTION = "conditions"
SCRIPTING_SCRIPT_COLLECTION = "scripts"

SCRIPTING_CONDITION_TYPE_QUERY_HAS_RESULTS = "queryHasResults"
SCRIPTING_CONDITION_TYPE_AND = "and"
SCRIPTING_CONDITION_TYPE_OR = "or"

SCRIPTING_EXECUTABLE_TYPE_AGGREGATED = "aggregated"
SCRIPTING_EXECUTABLE_TYPE_FIND = "find"
SCRIPTING_EXECUTABLE_TYPE_INSERT = "insert"
SCRIPTING_EXECUTABLE_TYPE_UPDATE = "update"
SCRIPTING_EXECUTABLE_TYPE_DELETE = "delete"

SCRIPTING_EXECUTABLE_TYPE_FILE_UPLOAD = "fileUpload"
SCRIPTING_EXECUTABLE_TYPE_FILE_DOWNLOAD = "fileDownload"
SCRIPTING_EXECUTABLE_TYPE_FILE_PROPERTIES = "fileProperties"
SCRIPTING_EXECUTABLE_TYPE_FILE_HASH = "fileHash"

SCRIPTING_EXECUTABLE_CALLER_DID = "$caller_did"
SCRIPTING_EXECUTABLE_CALLER_APP_DID = "$caller_app_did"
SCRIPTING_EXECUTABLE_PARAMS = "$params"
SCRIPTING_EXECUTABLE_DOWNLOADABLE = "_downloadable"
# scripting end

# other
VAULT_ORDER_COL = "vault_orders"
VAULT_ORDER_DID = "did"
VAULT_ORDER_APP_ID = "app_id"
VAULT_ORDER_PACKAGE_INFO = "package_info"
VAULT_ORDER_TXIDS = "pay_txids"
VAULT_ORDER_STATE = "state"
VAULT_ORDER_CREATE_TIME = "creat_time"
VAULT_ORDER_MODIFY_TIME = "modify_time"

VAULT_SERVICE_COL = "vault_service"
VAULT_SERVICE_DID = "did"
VAULT_SERVICE_APP_ID = "app_id"
VAULT_SERVICE_MAX_STORAGE = "max_storage"
VAULT_SERVICE_START_TIME = "start_time"
VAULT_SERVICE_END_TIME = "end_time"
VAULT_SERVICE_DELETE_TIME = "delete_time"
VAULT_SERVICE_EXPIRE_READ = "can_read_if_unpaid"
VAULT_SERVICE_STATE = "state"

