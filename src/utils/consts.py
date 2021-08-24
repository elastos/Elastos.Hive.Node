# -*- coding: utf-8 -*-

URL_DID_SIGN_IN = '/api/v2/did/signin'
URL_DID_AUTH = '/api/v2/did/auth'
URL_DID_BACKUP_AUTH = '/api/v2/did/backup_auth'
URL_BACKUP_SERVICE = '/api/v2/internal_backup/service'
URL_BACKUP_FINISH = '/api/v2/internal_backup/finished_confirmation'
URL_BACKUP_FILES = '/api/v2/internal_backup/files'
URL_BACKUP_FILE = '/api/v2/internal_backup/file'
URL_BACKUP_PATCH_HASH = '/api/v2/internal_backup/patch_hash'
URL_BACKUP_PATCH_DELTA = '/api/v2/internal_backup/patch_delta'
URL_BACKUP_PATCH_FILE = '/api/v2/internal_backup/patch_file'
URL_RESTORE_FINISH = '/api/v2/internal_restore/finished_confirmation'

URL_IPFS_BACKUP_PIN_CIDS = '/api/v2/ipfs-backup-internal/pin_cids'
URL_IPFS_BACKUP_GET_CIDS = '/api/v2/ipfs-backup-internal/get_cids'

BACKUP_FILE_SUFFIX = '.backup'

DID = 'did'
APP_DID = 'app_did'
OWNER_ID = 'owner_id'
CREATE_TIME = 'create_time'
MODIFY_TIME = 'modify_time'
SIZE = 'size'

COL_ORDERS = 'vault_backup_orders'
COL_ORDERS_SUBSCRIPTION = 'subscription'
COL_ORDERS_PRICING_NAME = 'pricing_name'
COL_ORDERS_ELA_AMOUNT = 'ela_amount'
COL_ORDERS_ELA_ADDRESS = 'ela_address'
COL_ORDERS_PROOF = 'proof'
COL_ORDERS_STATUS = 'status'

COL_ORDERS_STATUS_NORMAL = 'normal'
COL_ORDERS_STATUS_PAID = 'paid'
COL_ORDERS_STATUS_ARCHIVE = 'archive'

COL_RECEIPTS = 'vault_backup_receipts'
COL_RECEIPTS_ID = 'receipt_id'
COL_RECEIPTS_ORDER_ID = 'order_id'
COL_RECEIPTS_TRANSACTION_ID = 'transaction_id'
COL_RECEIPTS_PAID_DID = 'paid_did'

COL_IPFS_FILES = 'ipfs_files'
COL_IPFS_FILES_PATH = 'path'
COL_IPFS_FILES_SHA256 = 'sha256'
COL_IPFS_FILES_IS_FILE = 'is_file'
COL_IPFS_FILES_IPFS_CID = 'ipfs_cid'
