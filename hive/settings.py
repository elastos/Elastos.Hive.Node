import os
from pathlib import Path
from decouple import config, Config, RepositoryEnv
import logging


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
        return self.env_config('DID_RESOLVER', default="http://api.elastos.io:21606", cast=str)

    @property
    def ELA_RESOLVER(self):
        return self.env_config('ELA_RESOLVER', default="http://api.elastos.io:21606", cast=str)

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
        return self.env_config('HIVE_DATA', default="./data", cast=str)

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
    def MONGO_URI(self):
        return self.env_config('MONGO_URI', default="", cast=str)

    @property
    def MONGO_PASSWORD(self):
        return self.env_config('MONGO_PASSWORD', default="", cast=str)

    @property
    def MONGO_HOST(self):
        return self.env_config('MONGO_HOST', default="localhost", cast=str)

    @property
    def MONGO_PORT(self):
        return self.env_config('MONGO_PORT', default=27020, cast=int)

    @property
    def RCLONE_CONFIG_FILE_DIR(self):
        return self.env_config('RCLONE_CONFIG_FILE_DIR', default="./.rclone", cast=str)

    @property
    def HIVE_PAYMENT_CONFIG(self):
        return self.env_config('HIVE_PAYMENT_CONFIG', default="./payment_config.json", cast=str)

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



hive_setting = HiveSetting()


