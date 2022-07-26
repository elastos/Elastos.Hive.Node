import os
from pathlib import Path
from decouple import config, Config, RepositoryEnv
import logging

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
    def EID_RESOLVER_URL(self):
        return self.env_config('EID_RESOLVER_URL', default='https://api.elastos.io/eid', cast=str)

    @property
    def ESC_RESOLVER_URL(self):
        return self.env_config('ESC_RESOLVER_URL', default='https://api.elastos.io/ela', cast=str)

    @property
    def SERVICE_DID(self):
        return self.env_config('SERVICE_DID', default='', cast=str)

    @property
    def PASSPHRASE(self):
        return self.env_config('PASSPHRASE', default='', cast=str)

    @property
    def PASSWORD(self):
        return self.env_config('PASSWORD', default='password', cast=str)

    @property
    def DATA_STORE_PATH(self):
        value = self.env_config('DATA_STORE_PATH', default='./data', cast=str)
        if value.startswith('/'):
            return value
        return os.path.join(BASE_DIR, value)

    @property
    def VAULTS_BASE_DIR(self):
        return self.DATA_STORE_PATH + '/vaults'

    @property
    def BACKUP_VAULTS_BASE_DIR(self):
        return self.DATA_STORE_PATH + '/backup_vaults'

    @property
    def DID_DATA_BASE_DIR(self):
        return self.DATA_STORE_PATH + '/did'

    @property
    def DID_DATA_LOCAL_DIDS(self):
        return self.DID_DATA_BASE_DIR + '/localdids'

    @property
    def DID_DATA_STORE_PATH(self):
        return self.DID_DATA_BASE_DIR + '/store'

    @property
    def DID_DATA_CACHE_PATH(self):
        return self.DID_DATA_BASE_DIR + '/cache'

    @property
    def PAYMENT_CONFIG_PATH(self):
        path = self.env_config('PAYMENT_CONFIG_PATH', default='./payment_config.json', cast=str)
        if path.startswith('/'):
            return path
        return os.path.join(BASE_DIR, path)

    @property
    def PAYMENT_RECEIVING_ADDRESS(self):
        return self.env_config('PAYMENT_RECEIVING_ADDRESS', default='EN9YK69ScA6WFgVQW3UZcmSRLSCStaU2pQ', cast=str)

    @property
    def MONGODB_URI(self):
        return self.env_config('MONGODB_URI', default='mongodb://hive-mongo:27017', cast=str)

    @property
    def VERSION(self):
        return self.env_config('VERSION', default='2.4.1', cast=str)

    @property
    def LAST_COMMIT(self):
        return self.env_config('LAST_COMMIT', default='1dcc9178c12efefc786bc653bacec50a1f79161b', cast=str)

    @property
    def RCLONE_CONFIG_FILE_DIR(self):
        """ INFO: Just keep this item in this file, not required in .env. """
        return self.env_config('RCLONE_CONFIG_FILE_DIR', default='./.rclone_config', cast=str)

    @property
    def BACKUP_FTP_MASQUERADE_ADDRESS(self):
        """ INFO: Just keep this item in this file, not required in .env. """
        return self.env_config('BACKUP_FTP_MASQUERADE_ADDRESS', default='0.0.0.0', cast=str)

    @property
    def BACKUP_FTP_PASSIVE_PORTS_START(self):
        """ INFO: Just keep this item in this file, not required in .env. """
        return self.env_config('BACKUP_FTP_PASSIVE_PORTS_START', default=8301, cast=int)

    @property
    def BACKUP_FTP_PASSIVE_PORTS_END(self):
        """ INFO: Just keep this item in this file, not required in .env. """
        return self.env_config('BACKUP_FTP_PASSIVE_PORTS_END', default=8400, cast=int)

    @property
    def MONGO_URI(self):
        """ INFO: Just keep this item in this file, not required in .env. """
        return self.env_config('MONGO_URI', default='', cast=str)

    @property
    def AUTH_CHALLENGE_EXPIRED(self):
        return 3 * 60

    @property
    def ACCESS_TOKEN_EXPIRED(self):
        return 30 * 24 * 60 * 60


hive_setting = HiveSetting()
