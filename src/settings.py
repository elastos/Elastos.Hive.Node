"""
Comes from hive folder.
TODO: need refine this file later after v1 APIs have been removed.
"""

from pathlib import Path
from decouple import config, Config, RepositoryEnv
import logging

import os

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')


class HiveSetting:
    def __init__(self):
        self.env_config = config

    def init_config(self, hive_config='/etc/hive/.env'):
        env_dist = os.environ
        if "HIVE_CONFIG" in env_dist:
            hive_config = env_dist["HIVE_CONFIG"]
        config_file = Path(hive_config).resolve()
        if config_file.exists():
            self.env_config = Config(RepositoryEnv(config_file.as_posix()))
            logging.getLogger("Setting").debug("Config file is:" + config_file.as_posix())
            print("Setting Config file is:" + config_file.as_posix())

    @property
    def DID_RESOLVER(self):
        return self.env_config('DID_RESOLVER', default="https://api-testnet.elastos.io/newid", cast=str)

    @property
    def ELA_RESOLVER(self):
        return self.env_config('ELA_RESOLVER', default="https://api-testnet.elastos.io/ela", cast=str)

    @property
    def DID_MNEMONIC(self):
        return self.env_config('DID_MNEMONIC',
                               default="advance duty suspect finish space matter squeeze elephant twenty over stick shield",
                               cast=str)

    @property
    def DID_PASSPHRASE(self):
        return self.env_config('DID_PASSPHRASE', default="", cast=str)

    @property
    def DID_STOREPASS(self):
        return self.env_config('DID_STOREPASS', default="password", cast=str)

    @property
    def HIVE_DATA(self):
        value = self.env_config('HIVE_DATA', default="./data", cast=str)
        if value.startswith('/'):
            return value
        return os.path.join(BASE_DIR, value)

    @property
    def VAULTS_BASE_DIR(self):
        return self.HIVE_DATA + "/vaults"

    @property
    def BACKUP_VAULTS_BASE_DIR(self):
        return self.HIVE_DATA + "/backup_vaults"

    @property
    def DID_DATA_BASE_DIR(self):
        return self.HIVE_DATA + "/did"

    @property
    def DID_DATA_LOCAL_DIDS(self):
        return self.DID_DATA_BASE_DIR + "/localdids"

    @property
    def DID_DATA_STORE_PATH(self):
        return self.DID_DATA_BASE_DIR + "/store"

    @property
    def DID_DATA_CACHE_PATH(self):
        return self.DID_DATA_BASE_DIR + "/cache"

    @property
    def BACKUP_FTP_PORT(self):
        return self.env_config('BACKUP_FTP_PORT', default=2121, cast=int)

    @property
    def BACKUP_FTP_MASQUERADE_ADDRESS(self):
        return self.env_config('BACKUP_FTP_MASQUERADE_ADDRESS', default="0.0.0.0", cast=str)

    @property
    def BACKUP_FTP_PASSIVE_PORTS_START(self):
        return self.env_config('BACKUP_FTP_PASSIVE_PORTS_START', default=8301, cast=int)

    @property
    def BACKUP_FTP_PASSIVE_PORTS_END(self):
        return self.env_config('BACKUP_FTP_PASSIVE_PORTS_END', default=8400, cast=int)

    @property
    def MONGO_TYPE(self):
        return self.env_config('MONGO_TYPE', default="", cast=str)

    @property
    def MONGO_URI(self):
        """ TODO: to be removed """
        return self.env_config('MONGO_URI', default="", cast=str)

    @property
    def MONGO_PASSWORD(self):
        """ TODO: to be removed """
        return self.env_config('MONGO_PASSWORD', default="", cast=str)

    @property
    def MONGO_HOST(self):
        return self.env_config('MONGO_HOST', default="localhost", cast=str)

    @property
    def MONGO_PORT(self):
        return self.env_config('MONGO_PORT', default=27020, cast=int)

    def is_mongodb_atlas(self):
        return self.MONGO_TYPE == 'atlas'

    @property
    def RCLONE_CONFIG_FILE_DIR(self):
        return self.env_config('RCLONE_CONFIG_FILE_DIR', default="./.rclone", cast=str)

    @property
    def HIVE_PAYMENT_CONFIG(self):
        name = self.env_config('HIVE_PAYMENT_CONFIG', default='./payment_config.json', cast=str)
        return os.path.join(BASE_DIR, name)

    @property
    def HIVE_PAYMENT_ADDRESS(self):
        return self.env_config('HIVE_PAYMENT_ADDRESS', default='', cast=str)

    @property
    def HIVE_SENTRY_DSN(self):
        return self.env_config('HIVE_SENTRY_DSN', default="", cast=str)

    @property
    def AUTH_CHALLENGE_EXPIRED(self):
        return 3 * 60

    @property
    def ACCESS_TOKEN_EXPIRED(self):
        return 30 * 24 * 60 * 60

    @property
    def HIVE_VERSION(self):
        return self.env_config('HIVE_VERSION', default="0.0.0", cast=str)

    @property
    def HIVE_COMMIT_HASH(self):
        return self.env_config('HIVE_COMMIT_HASH', default="", cast=str)

    @property
    def LANGUAGE(self):
        return "english"

    @property
    def ENABLE_IPFS(self):
        return self.env_config('ENABLE_IPFS', default='False', cast=bool)

    @property
    def IPFS_NODE_URL(self):
        return self.env_config('IPFS_NODE_URL', default='', cast=str)

    @property
    def IPFS_PROXY_URL(self):
        return self.env_config('IPFS_PROXY_URL', default='', cast=str)

    @property
    def PAYMENT_CHECK_EXPIRED(self):
        return self.env_config('PAYMENT_CHECK_EXPIRED', default='True', cast=bool)

    def BACKUP_IS_SYNC(self):
        return self.env_config('BACKUP_IS_SYNC', default='False', cast=bool)

    @property
    def ENABLE_CORS(self):
        return self.env_config('ENABLE_CORS', default='False', cast=bool)


hive_setting = HiveSetting()
