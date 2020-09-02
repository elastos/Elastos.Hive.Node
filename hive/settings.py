from decouple import config

DID_SIDECHAIN_URL = config('DID_SIDECHAIN_URL', default="http://api.elastos.io:21606", cast=str)

MONGO_HOST = config('MONGO_HOST', default="localhost", cast=str)
MONGO_PORT = config('MONGO_PORT', default=27020, cast=int)

DID_BASE_DIR = config('DID_BASE_DIR', default="./did_user_data", cast=str)
DID_CHALLENGE_EXPIRE = 3 * 60
DID_TOKEN_EXPIRE = 30 * 24 * 60 * 60
RCLONE_CONFIG_FILE = config('RCLONE_CONFIG_FILE', default="/.config/rclone/rclone.conf", cast=str)