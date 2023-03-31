# -*- coding: utf-8 -*-

###############################################################################
# constant variables from v1
###############################################################################

# @deprecated compatible with v1
# HIVE_MODE_DEV = "dev"
HIVE_MODE_PROD = "prod"  # for normal run
HIVE_MODE_TEST = "test"  # run on v1 test cases

# for files service
CHUNK_SIZE = 4096
USER_DID = "userDid"
APP_ID = "appDid"
APP_INSTANCE_DID = "appInstanceDid"

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

OWNER_ID = 'owner_id'
CREATE_TIME = 'create_time'
MODIFY_TIME = 'modify_time'
STATE = 'state'
STATE_RUNNING = 'running'
STATE_FINISH = 'finish'
STATE_FAILED = 'failed'
ORIGINAL_SIZE = 'original_size'
IS_UPGRADED = 'is_upgraded'
VERSION = 'version'

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

###############################################################################
# common field for collections
###############################################################################

# TODO: make these internal
USR_DID = 'user_did'

###############################################################################
# management tables definition
###############################################################################

# for backup service

# VAULT_BACKUP_SERVICE_COL = "vault_backup_service"  # management table, only for v1
VAULT_BACKUP_SERVICE_USING = "backup_using"  # pricing name
VAULT_BACKUP_SERVICE_MAX_STORAGE = "max_storage"
VAULT_BACKUP_SERVICE_USE_STORAGE = "use_storage"
VAULT_BACKUP_SERVICE_START_TIME = "start_time"
VAULT_BACKUP_SERVICE_END_TIME = "end_time"

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
# end of backup service

# for order
COL_ORDERS = 'vault_order'  # management table
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
# end of order

# for vault collection, must compatible with v1
VAULT_SERVICE_COL = "vault_service"  # management table
VAULT_SERVICE_DID = "did"  # user_did
VAULT_SERVICE_MAX_STORAGE = "max_storage"
VAULT_SERVICE_FILE_USE_STORAGE = "file_use_storage"
VAULT_SERVICE_DB_USE_STORAGE = "db_use_storage"
VAULT_SERVICE_MODIFY_TIME = "modify_time"
VAULT_SERVICE_START_TIME = "start_time"
VAULT_SERVICE_END_TIME = "end_time"
VAULT_SERVICE_PRICING_USING = "pricing_using"
VAULT_SERVICE_STATE = "state"  # maybe not exists

VAULT_SERVICE_STATE_RUNNING = "running"  # read and write
VAULT_SERVICE_STATE_FREEZE = "freeze"  # read, but not write
VAULT_SERVICE_STATE_REMOVED = "removed"  # soft unsubscribe

VAULT_SERVICE_LATEST_ACCESS_TIME = "latest_access_time"  # for access checking on database, files, scripting.
# constants of db end


def get_unique_dict_item_from_list(dict_list: list) -> list:
    if not dict_list:
        return list()
    return list({frozenset(item.items()): item for item in dict_list}.values())
