# -*- coding: utf-8 -*-

# @deprecated compatible with v1
# HIVE_MODE_DEV = "dev"
HIVE_MODE_PROD = "prod"  # for normal run
HIVE_MODE_TEST = "test"  # run on v1 test cases

# for files service
USER_DID = "userDid"
APP_ID = "appDid"
APP_INSTANCE_DID = "appInstanceDid"

URL_V1 = '/api/v1'
URL_V2 = '/api/v2'
URL_SIGN_IN = '/did/signin'
URL_AUTH = '/did/auth'
URL_BACKUP_AUTH = '/did/backup_auth'
URL_SERVER_INTERNAL_BACKUP = '/vault-backup-service/backup'
URL_SERVER_INTERNAL_RESTORE = '/vault-backup-service/restore'
URL_SERVER_INTERNAL_STATE = '/vault-backup-service/state'

VERSION = 'version'  # only for order

###############################################################################
# common field for collections
###############################################################################

# TODO: make these internal
USR_DID = 'user_did'

###############################################################################
# management tables definition
###############################################################################

# for backup service

COL_IPFS_BACKUP_CLIENT = 'ipfs_backup_client'

BACKUP_TARGET_TYPE = 'type'  # backup client
BACKUP_TARGET_TYPE_HIVE_NODE = 'hive_node'
BACKUP_TARGET_TYPE_GOOGLE_DRIVER = 'google_driver'

BACKUP_REQUEST_ACTION = 'action'  # backup client
BACKUP_REQUEST_ACTION_BACKUP = 'backup'  # the following two actions merge with BackupRequestAction
BACKUP_REQUEST_ACTION_RESTORE = 'restore'

BACKUP_REQUEST_STATE = 'state'  # backup client
BACKUP_REQUEST_STATE_STOP = 'stop'  # the following five states merge with BackupRequestAction
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


def get_unique_dict_item_from_list(dict_list: list) -> list:
    if not dict_list:
        return list()
    return list({frozenset(item.items()): item for item in dict_list}.values())
