# constants of db start
DID_INFO_DB_NAME = "hive_manage_info"

# for auth collection, must compatible with v1
# this collection is treated as the temporary one for signin/auth, do not dependent on it for long usage.
DID_INFO_REGISTER_COL = "auth_register"
USER_DID = "userDid"  # added when /auth
APP_ID = "appDid"  # added when /auth
APP_INSTANCE_DID = "appInstanceDid"  # added when /signin
DID_INFO_NONCE = "nonce"
DID_INFO_TOKEN = "token"
DID_INFO_NONCE_EXPIRED = "nonce_expired"
DID_INFO_TOKEN_EXPIRED = "token_expired"
# auth_register end

# for vault collection, must compatible with v1
VAULT_SERVICE_COL = "vault_service"  # collection name
VAULT_SERVICE_DID = "did"  # user_did
VAULT_SERVICE_MAX_STORAGE = "max_storage"
VAULT_SERVICE_FILE_USE_STORAGE = "file_use_storage"
VAULT_SERVICE_DB_USE_STORAGE = "db_use_storage"
VAULT_SERVICE_MODIFY_TIME = "modify_time"
VAULT_SERVICE_START_TIME = "start_time"
VAULT_SERVICE_END_TIME = "end_time"
VAULT_SERVICE_PRICING_USING = "pricing_using"
VAULT_SERVICE_STATE = "state"

VAULT_SERVICE_STATE_RUNNING = "running"  # read and write
VAULT_SERVICE_STATE_FREEZE = "freeze"  # read, but not write

VAULT_SERVICE_LATEST_ACCESS_TIME = "latest_access_time"  # for access checking on database, files, scripting.
# constants of db end

# for backup server collection
VAULT_BACKUP_SERVICE_COL = "vault_backup_service"
VAULT_BACKUP_SERVICE_USING = "backup_using"  # pricing_name
VAULT_BACKUP_SERVICE_MAX_STORAGE = "max_storage"
VAULT_BACKUP_SERVICE_USE_STORAGE = "use_storage"
VAULT_BACKUP_SERVICE_START_TIME = "start_time"
VAULT_BACKUP_SERVICE_END_TIME = "end_time"
# end backup server collection

# scripting begin, compatible with v1
SCRIPTING_SCRIPT_COLLECTION = "scripts"
SCRIPTING_SCRIPT_TEMP_TX_COLLECTION = "scripts_temptx"

SCRIPTING_CONDITION_TYPE_QUERY_HAS_RESULTS = "queryHasResults"
SCRIPTING_CONDITION_TYPE_AND = "and"
SCRIPTING_CONDITION_TYPE_OR = "or"

SCRIPTING_EXECUTABLE_TYPE_AGGREGATED = "aggregated"
SCRIPTING_EXECUTABLE_TYPE_FIND = "find"
SCRIPTING_EXECUTABLE_TYPE_COUNT = "count"
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

# @deprecated compatible with v1
# HIVE_MODE_DEV = "dev"
HIVE_MODE_PROD = "prod"  # for normal run
HIVE_MODE_TEST = "test"  # run on v1 test cases

# for files service
CHUNK_SIZE = 4096
