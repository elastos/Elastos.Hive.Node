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
ELA_RESOLVER = env_config('ELA_RESOLVER', default="http://api.elastos.io:21606", cast=str)

DID_MNEMONIC = env_config('DID_MNEMONIC',
                          default="advance duty suspect finish space matter squeeze elephant twenty over stick shield",
                          cast=str)
DID_PASSPHRASE = env_config('DID_PASSPHRASE', default="", cast=str)
DID_STOREPASS = env_config('DID_STOREPASS', default="password", cast=str)
HIVE_DATA = env_config('HIVE_DATA', default="./data", cast=str)
VAULTS_BASE_DIR = HIVE_DATA + "/vaults"
BACKUP_VAULTS_BASE_DIR = HIVE_DATA + "/backup_vaults"

MONGO_HOST = env_config('MONGO_HOST', default="localhost", cast=str)
MONGO_PORT = env_config('MONGO_PORT', default=27020, cast=int)

RCLONE_CONFIG_FILE_DIR = env_config('RCLONE_CONFIG_FILE_DIR', default="./.rclone", cast=str)
HIVE_PAYMENT_CONFIG = env_config('HIVE_PAYMENT_CONFIG', default="./payment_config.json", cast=str)
HIVE_SENTRY_DSN = env_config('HIVE_SENTRY_DSN', default="", cast=str)

AUTH_CHALLENGE_EXPIRED = 3 * 60
ACCESS_TOKEN_EXPIRED = 30 * 24 * 60 * 60

HIVE_VERSION = env_config('HIVE_VERSION', default="0.0.0", cast=str)
HIVE_COMMIT_HASH = env_config('HIVE_COMMIT_HASH', default="", cast=str)
