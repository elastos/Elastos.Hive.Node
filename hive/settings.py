from decouple import config

DID_SIDECHAIN_URL = config('DID_SIDECHAIN_URL', default="http://api.elastos.io:21606", cast=str)

MONGO_HOST = config('MONGO_HOST', default="localhost", cast=str)
MONGO_PORT = config('MONGO_PORT', default=27020, cast=int)
MONGO_DBNAME = config('MONGO_DBNAME', default="hivedb", cast=str)

RESOURCE_METHODS = ['GET', 'POST', 'DELETE']

ITEM_METHODS = ['GET', 'PATCH', 'PUT', 'DELETE']

CACHE_CONTROL = 'max-age=20'
CACHE_EXPIRES = 20

URL_PREFIX = 'api/v1/db/col'

DOMAIN = {
}
DID_BASE_DIR = config('DID_BASE_DIR', default="./did_user_data", cast=str)
DID_CHALLENGE_EXPIRE = 15 * 60
DID_TOKEN_EXPIRE = 24 * 60 * 60
RCLONE_CONFIG_FILE = config('RCLONE_CONFIG_FILE', default="/.config/rclone/rclone.conf", cast=str)