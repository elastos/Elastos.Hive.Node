# -*- coding: utf-8 -*-

###############################################################################
# constant variables from v1
###############################################################################

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

###############################################################################
# constant variables added by v2
###############################################################################

URL_V1 = '/api/v1'
URL_V2 = '/api/v2'
URL_SIGN_IN = '/did/signin'
URL_AUTH = '/did/auth'
URL_BACKUP_AUTH = '/did/backup_auth'
URL_SERVER_INTERNAL_BACKUP = '/vault-backup-service/backup'
URL_SERVER_INTERNAL_RESTORE = '/vault-backup-service/restore'
URL_SERVER_INTERNAL_STATE = '/vault-backup-service/state'

BACKUP_FILE_SUFFIX = '.backup'

DID = 'did'
USR_DID = 'user_did'
APP_DID = 'app_did'
OWNER_ID = 'owner_id'
CREATE_TIME = 'create_time'
MODIFY_TIME = 'modify_time'
SIZE = 'size'
STATE = 'state'
STATE_RUNNING = 'running'
STATE_FINISH = 'finish'
STATE_FAILED = 'failed'
ORIGINAL_SIZE = 'original_size'
IS_UPGRADED = 'is_upgraded'
CID = 'cid'
COUNT = 'count'
VERSION = 'version'

# for user did and app did relations
COL_APPLICATION = 'application'
COL_APPLICATION_USR_DID = USR_DID
COL_APPLICATION_APP_DID = APP_DID
COL_APPLICATION_DATABASE_NAME = 'database_name'
COL_APPLICATION_STATE = STATE
# extra: 'created' and 'modified'
COL_APPLICATION_STATE_NORMAL = 'normal'
# COL_APPLICATION_STATE_REMOVED = 'removed'

# for the order collection
COL_ORDERS = 'vault_order'
COL_ORDERS_SUBSCRIPTION = 'subscription'
COL_ORDERS_PRICING_NAME = 'pricing_name'
COL_ORDERS_ELA_AMOUNT = 'ela_amount'
COL_ORDERS_ELA_ADDRESS = 'ela_address'
COL_ORDERS_EXPIRE_TIME = 'expire_time'
COL_ORDERS_CONTRACT_ORDER_ID = 'contract_order_id'
COL_ORDERS_PROOF = 'proof'
COL_ORDERS_STATUS = 'status'

COL_ORDERS_STATUS_NORMAL = 'normal'
COL_ORDERS_STATUS_EXPIRED = 'expired'  # not paid
COL_ORDERS_STATUS_PAID = 'paid'
COL_ORDERS_STATUS_ARCHIVE = 'archive'

# for receipt, contains some fields of order collection
COL_RECEIPTS = 'vault_receipt'
COL_RECEIPTS_ORDER_ID = 'order_id'
COL_RECEIPTS_PAID_DID = 'paid_did'
# order end

COL_IPFS_FILES = 'ipfs_files'
COL_IPFS_FILES_PATH = 'path'
COL_IPFS_FILES_SHA256 = 'sha256'
COL_IPFS_FILES_IS_FILE = 'is_file'
COL_IPFS_FILES_IPFS_CID = 'ipfs_cid'
COL_IPFS_FILES_IS_ENCRYPT = 'is_encrypt'
COL_IPFS_FILES_ENCRYPT_METHOD = 'encrypt_method'

COL_IPFS_CID_REF = 'ipfs_cid_ref'

COL_IPFS_BACKUP_CLIENT = 'ipfs_backup_client'
COL_IPFS_BACKUP_SERVER = 'ipfs_backup_server'

BACKUP_TARGET_TYPE = 'type'
BACKUP_TARGET_TYPE_HIVE_NODE = 'hive_node'
BACKUP_TARGET_TYPE_GOOGLE_DRIVER = 'google_driver'

BACKUP_REQUEST_ACTION = 'action'
BACKUP_REQUEST_ACTION_BACKUP = 'backup'
BACKUP_REQUEST_ACTION_RESTORE = 'restore'

BACKUP_REQUEST_STATE = 'state'
BACKUP_REQUEST_STATE_STOP = 'stop'
BACKUP_REQUEST_STATE_PROCESS = 'process'
BACKUP_REQUEST_STATE_SUCCESS = 'success'
BACKUP_REQUEST_STATE_FAILED = 'failed'
BACKUP_REQUEST_STATE_MSG = 'state_msg'

BACKUP_REQUEST_TARGET_HOST = 'target_host'
BACKUP_REQUEST_TARGET_DID = 'target_did'
BACKUP_REQUEST_TARGET_TOKEN = 'target_token'

# For backup subscription.
BKSERVER_REQ_ACTION = 'req_action'
BKSERVER_REQ_STATE = 'req_state'
BKSERVER_REQ_STATE_MSG = 'req_state_msg'
BKSERVER_REQ_CID = 'req_cid'
BKSERVER_REQ_SHA256 = 'req_sha256'
BKSERVER_REQ_SIZE = 'req_size'
BKSERVER_REQ_PUBLIC_KEY = 'public_key'

# @deprecated
URL_BACKUP_SERVICE = '/api/v2/internal_backup/service'
URL_BACKUP_FINISH = '/api/v2/internal_backup/finished_confirmation'
URL_BACKUP_FILES = '/api/v2/internal_backup/files'
URL_BACKUP_FILE = '/api/v2/internal_backup/file'
URL_BACKUP_PATCH_HASH = '/api/v2/internal_backup/patch_hash'
URL_BACKUP_PATCH_DELTA = '/api/v2/internal_backup/patch_delta'
URL_BACKUP_PATCH_FILE = '/api/v2/internal_backup/patch_file'
URL_RESTORE_FINISH = '/api/v2/internal_restore/finished_confirmation'
URL_IPFS_BACKUP_PIN_CIDS = '/api/v2/ipfs-backup-internal/pin_cids'
URL_IPFS_BACKUP_GET_DBFILES = '/api/v2/ipfs-backup-internal/get_dbfiles'
URL_IPFS_BACKUP_STATE = '/api/v2/ipfs-backup-internal/state'


def get_unique_dict_item_from_list(dict_list: list) -> list:
    if not dict_list:
        return list()
    return list({frozenset(item.items()): item for item in dict_list}.values())
