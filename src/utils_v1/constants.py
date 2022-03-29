# constants of db start
DID_INFO_DB_NAME = "hive_manage_info"

DID_INFO_REGISTER_COL = "auth_register"
USER_DID = "userDid"  # compatible with v1
APP_ID = "appDid"
APP_INSTANCE_DID = "appInstanceDid"
DID_INFO_NONCE = "nonce"
DID_INFO_TOKEN = "token"
DID_INFO_NONCE_EXPIRED = "nonce_expired"
DID_INFO_TOKEN_EXPIRED = "token_expired"

DID_SYNC_INFO_COL = "did_sync_info"
DID_SYNC_INFO_STATE = "state"
DID_SYNC_INFO_MSG = "msg"
DID_SYNC_INFO_TIME = "time"
DID_SYNC_INFO_DRIVE = "drive"

VAULT_BACKUP_INFO_COL = "vault_backup_info"
VAULT_BACKUP_INFO_TYPE = "type"
VAULT_BACKUP_INFO_STATE = "state"
VAULT_BACKUP_INFO_MSG = "msg"
VAULT_BACKUP_INFO_TIME = "time"
VAULT_BACKUP_INFO_DRIVE = "drive"
VAULT_BACKUP_INFO_TOKEN = "token"

VAULT_BACKUP_INFO_TYPE_GOOGLE_DRIVE = "google_drive"
VAULT_BACKUP_INFO_TYPE_HIVE_NODE = "hive_node"

VAULT_ORDER_COL = "vault_orders"
# VAULT_ORDER_DID = "did"
VAULT_ORDER_APP_ID = "app_id"
VAULT_ORDER_PACKAGE_INFO = "pricing_info"
VAULT_ORDER_TXIDS = "pay_txids"
VAULT_ORDER_STATE = "state"
VAULT_ORDER_TYPE = "type"
VAULT_ORDER_CREATE_TIME = "creat_time"
VAULT_ORDER_PAY_TIME = "pay_time"
VAULT_ORDER_MODIFY_TIME = "modify_time"

VAULT_SERVICE_COL = "vault_service"
VAULT_SERVICE_DID = "did"  # compatible with v1
VAULT_SERVICE_MAX_STORAGE = "max_storage"
VAULT_SERVICE_FILE_USE_STORAGE = "file_use_storage"
VAULT_SERVICE_DB_USE_STORAGE = "db_use_storage"
VAULT_SERVICE_MODIFY_TIME = "modify_time"
VAULT_SERVICE_START_TIME = "start_time"
VAULT_SERVICE_END_TIME = "end_time"
VAULT_SERVICE_PRICING_USING = "pricing_using"
VAULT_SERVICE_STATE = "state"
# constants of db end

VAULT_BACKUP_SERVICE_COL = "vault_backup_service"
VAULT_BACKUP_SERVICE_DID = "did"  # only for v1
VAULT_BACKUP_SERVICE_MAX_STORAGE = "max_storage"
VAULT_BACKUP_SERVICE_USE_STORAGE = "use_storage"
VAULT_BACKUP_SERVICE_MODIFY_TIME = "modify_time"
VAULT_BACKUP_SERVICE_START_TIME = "start_time"
VAULT_BACKUP_SERVICE_END_TIME = "end_time"
VAULT_BACKUP_SERVICE_USING = "backup_using"
VAULT_BACKUP_SERVICE_STATE = "state"

# scripting begin
SCRIPTING_SCRIPT_COLLECTION = "scripts"
SCRIPTING_SCRIPT_TEMP_TX_COLLECTION = "scripts_temptx"

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

# pubsub start
PUB_CHANNEL_COLLECTION = "pub_channel_col"
PUB_CHANNEL_ID = "channel_id"
PUB_CHANNEL_PUB_DID = "pub_did"
PUB_CHANNEL_PUB_APPID = "pub_appid"
PUB_CHANNEL_NAME = "channel_name"
PUB_CHANNEL_SUB_DID = "sub_did"
PUB_CHANNEL_SUB_APPID = "sub_appid"
PUB_CHANNEL_MODIFY_TIME = "modify_time"

SUB_MESSAGE_COLLECTION = "sub_message_col"
SUB_MESSAGE_SUBSCRIBE_ID = "subscribe_id"
SUB_MESSAGE_PUB_DID = "pub_did"
SUB_MESSAGE_PUB_APPID = "pub_appid"
SUB_MESSAGE_CHANNEL_NAME = "channel_name"
SUB_MESSAGE_SUB_DID = "sub_did"
SUB_MESSAGE_SUB_APPID = "sub_appid"
SUB_MESSAGE_DATA = "message_data"
SUB_MESSAGE_TIME = "message_time"
SUB_MESSAGE_MODIFY_TIME = "modify_time"
# pubsub end

# other
VAULT_ACCESS_WR = "vault_write_read"
VAULT_ACCESS_R = "vault_read"
VAULT_ACCESS_DEL = "vault_delete"


VAULT_STORAGE_DB = "vault_db"
VAULT_STORAGE_FILE = "vault_file"

BACKUP_ACCESS = "backup_access"

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

DID_AUTH_SUBJECT = "didauth"
DID_AUTH_REALM = "elastos_hive_node"

HIVE_MODE_DEV = "dev"
HIVE_MODE_PROD = "prod"
HIVE_MODE_TEST = "test"

INTER_BACKUP_SERVICE_URL = '/api/v1/inter/backup/service'
INTER_BACKUP_SAVE_FINISH_URL = '/api/v1/inter/backup/save_finish'
INTER_BACKUP_RESTORE_FINISH_URL = '/api/v1/inter/backup/restore_finish'

INTER_BACKUP_FILE_LIST_URL = '/api/v1/inter/backup/file_list'
INTER_BACKUP_FILE_URL = '/api/v1/inter/backup/file'
INTER_BACKUP_MOVE_FILE_URL = '/api/v1/inter/backup/move'
INTER_BACKUP_COPY_FILE_URL = '/api/v1/inter/backup/copy'
INTER_BACKUP_PATCH_HASH_URL = '/api/v1/inter/backup/patch/hash'
INTER_BACKUP_PATCH_DELTA_URL = '/api/v1/inter/backup/patch/delta'
INTER_BACKUP_GENE_DELTA_URL = '/api/v1/inter/backup/gene/delta'


CHUNK_SIZE = 4096
