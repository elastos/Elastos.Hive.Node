# -*- coding: utf-8 -*-

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

COL_ORDERS = 'vault_order'
COL_ORDERS_SUBSCRIPTION = 'subscription'
COL_ORDERS_PRICING_NAME = 'pricing_name'
COL_ORDERS_ELA_AMOUNT = 'ela_amount'
COL_ORDERS_ELA_ADDRESS = 'ela_address'
COL_ORDERS_PROOF = 'proof'
COL_ORDERS_STATUS = 'status'

COL_ORDERS_STATUS_NORMAL = 'normal'
COL_ORDERS_STATUS_PAID = 'paid'
COL_ORDERS_STATUS_ARCHIVE = 'archive'

COL_RECEIPTS = 'vault_receipt'
COL_RECEIPTS_ID = 'receipt_id'
COL_RECEIPTS_ORDER_ID = 'order_id'
COL_RECEIPTS_TRANSACTION_ID = 'transaction_id'
COL_RECEIPTS_PAID_DID = 'paid_did'

COL_IPFS_FILES = 'ipfs_files'
COL_IPFS_FILES_PATH = 'path'
COL_IPFS_FILES_SHA256 = 'sha256'
COL_IPFS_FILES_IS_FILE = 'is_file'
COL_IPFS_FILES_IPFS_CID = 'ipfs_cid'

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
BACKUP_REQUEST_STATE_INPROGRESS = 'process'
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


def get_unique_dict_item_from_list(dict_list: list):
    if not dict_list:
        return list()
    return list({frozenset(item.items()): item for item in dict_list}.values())
