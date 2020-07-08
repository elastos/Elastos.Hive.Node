DID_PREFIX = "_did_prefix"
DID_DB_PREFIX = "did_of_"

DID_INFO_DB_NAME = "did_info"
DID_INFO_REGISTER_COL = "did_register"
DID = "did"
APP_ID = "app_id"
DID_INFO_NONCE = "nonce"
DID_INFO_TOKEN = "token"
DID_INFO_NONCE_EXPIRE = "nonce_expire"
DID_INFO_TOKEN_EXPIRE = "token_expire"

DID_RESOURCE_COL = "did_col_schemas"
DID_RESOURCE_DID = "did"
DID_RESOURCE_NAME = "name"
DID_RESOURCE_SCHEMA = "schema"

FILE_INFO_DB_NAME = "file_info"
FILE_INFO_COL = "did_file_info"
FILE_INFO_BELONG_DID = "belong_did"
FILE_INFO_BELONG_APP_ID = "belong_app_id"
FILE_INFO_FILE_NAME = "file_name"
FILE_INFO_FILE_SIZE = "file_size"
FILE_INFO_FILE_CREATE_TIME = "file_create_time"
FILE_INFO_FILE_MODIFY_TIME = "file_modify_time"

DID_FILE_DIR = "./did_file"
DID_CHALLENGE_EXPIRE = 15 * 60
DID_TOKEN_EXPIRE = 24 * 60 * 60

DID_AUTH_SUBJECT = "didauth"
DID_AUTH_REALM = "elastos_hive_node"

RCLONE_CONFIG_FILE = "/.config/rclone/rclone.conf"


def did_tail_part(did):
    return did.split(":")[2]
