from decouple import config

DID_SIDECHAIN_URL = config('DID_SIDECHAIN_URL', default="http://api.elastos.io:21606", cast=str)

DID_MNEMONIC = config('DID_MNEMONIC',
                      default="advance duty suspect finish space matter squeeze elephant twenty over stick shield",
                      cast=str)
DID_PASSPHRASE = config('DID_PASSPHRASE', default="secret", cast=str)
DID_STOREPASS = config('DID_STOREPASS', default="password", cast=str)
HIVE_DATA_PATH = config('HIVE_DATA', default="./data", cast=str)

MONGO_HOST = config('MONGO_HOST', default="localhost", cast=str)
MONGO_PORT = config('MONGO_PORT', default=27020, cast=int)

VAULTS_BASE_DIR = HIVE_DATA_PATH + "/vaults"
AUTH_CHALLENGE_EXPIRED = 3 * 60
ACCESS_TOKEN_EXPIRED = 30 * 24 * 60 * 60
RCLONE_CONFIG_FILE = config('RCLONE_CONFIG_FILE', default="/.config/rclone/rclone.conf", cast=str)
