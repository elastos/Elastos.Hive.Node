import os
from pathlib import Path
from decouple import config, Config, RepositoryEnv
import logging

HIVE_CONFIG = '/etc/hive/.env'

env_dist = os.environ
if "HIVE_CONFIG" in env_dist:
    HIVE_CONFIG = env_dist["HIVE_CONFIG"]

config_file = Path(HIVE_CONFIG).resolve()
if config_file.exists():
    env_config = Config(RepositoryEnv(HIVE_CONFIG))
    logging.debug("Config file is " + HIVE_CONFIG)
else:
    env_config = config
    logging.debug("Autoconfig")

DID_RESOLVER = env_config('DID_RESOLVER', default="http://api.elastos.io:21606", cast=str)

DID_MNEMONIC = env_config('DID_MNEMONIC',
                          default="advance duty suspect finish space matter squeeze elephant twenty over stick shield",
                          cast=str)
DID_PASSPHRASE = env_config('DID_PASSPHRASE', default="secret", cast=str)
DID_STOREPASS = env_config('DID_STOREPASS', default="password", cast=str)
HIVE_DATA = env_config('HIVE_DATA', default="./data", cast=str)
VAULTS_BASE_DIR = HIVE_DATA + "/vaults"

MONGO_HOST = env_config('MONGO_HOST', default="localhost", cast=str)
MONGO_PORT = env_config('MONGO_PORT', default=27020, cast=int)

RCLONE_CONFIG_FILE = env_config('RCLONE_CONFIG_FILE', default="/.config/rclone/rclone.conf", cast=str)

AUTH_CHALLENGE_EXPIRED = 3 * 60
ACCESS_TOKEN_EXPIRED = 30 * 24 * 60 * 60
