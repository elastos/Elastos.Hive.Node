from pathlib import Path
from decouple import config, Config, RepositoryEnv
import logging

import os

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')


class HiveSetting:
    def __init__(self):
        self.env_config = config

    def init_config(self, hive_config='/etc/hive/.env'):
        hive_config = os.environ.get('HIVE_CONFIG', hive_config)
        config_file = Path(hive_config).resolve()
        if config_file.exists():
            self.env_config = Config(RepositoryEnv(config_file.as_posix()))
            logging.info(f'User defined config file: {config_file.as_posix()}')

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
    def NODE_CREDENTIAL(self):
        return self.env_config('NODE_CREDENTIAL', default='', cast=str)

    @property
    def DATA_STORE_PATH(self):
        path = self.env_config('DATA_STORE_PATH', default='./data', cast=str)
        if path.startswith('/'):
            return path
        return os.path.join(BASE_DIR, path)

    @property
    def VAULTS_BASE_DIR(self):
        return self.DATA_STORE_PATH + '/vaults'

    def get_user_vault_path(self, user_did: str) -> Path:
        """ get the user's vault local path which contains cache files etc. """
        return Path(self.VAULTS_BASE_DIR) / user_did.split(":")[2]

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
    def SENTRY_ENABLED(self):
        return self.env_config('SENTRY_ENABLED', default='False', cast=bool)

    @property
    def SENTRY_DSN(self):
        return self.env_config('SENTRY_DSN', default='', cast=str)

    @property
    def PAYMENT_ENABLED(self):
        return self.env_config('PAYMENT_ENABLED', default='True', cast=bool)

    @property
    def PAYMENT_CONFIG_PATH(self):
        path = self.env_config('PAYMENT_CONFIG_PATH', default='./payment_config.json', cast=str)
        if path.startswith('/'):
            return path
        return os.path.join(BASE_DIR, path)

    @property
    def PAYMENT_CONTRACT_URL(self):
        return self.env_config('PAYMENT_CONTRACT_URL', default='', cast=str)

    @property
    def PAYMENT_CONTRACT_ADDRESS(self):
        return self.env_config('PAYMENT_CONTRACT_ADDRESS', default='', cast=str)

    @property
    def PAYMENT_RECEIVING_ADDRESS(self):
        return self.env_config('PAYMENT_RECEIVING_ADDRESS', default='EN9YK69ScA6WFgVQW3UZcmSRLSCStaU2pQ', cast=str)

    @property
    def ATLAS_ENABLED(self):
        return self.env_config('ATLAS_ENABLED', default='False', cast=bool)

    @property
    def MONGODB_URI(self):
        return self.env_config('MONGODB_URI', default='mongodb://hive-mongo:27017', cast=str)

    @property
    def IPFS_NODE_URL(self):
        return self.env_config('IPFS_NODE_URL', default='http://hive-ipfs:5001', cast=str)

    @property
    def IPFS_GATEWAY_URL(self):
        return self.env_config('IPFS_GATEWAY_URL', default='http://hive-ipfs:8080', cast=str)

    @property
    def ENABLE_CORS(self):
        return self.env_config('ENABLE_CORS', default='True', cast=bool)

    @property
    def VERSION(self):
        return self.env_config('VERSION', default='2.4.1', cast=str)

    @property
    def LAST_COMMIT(self):
        return self.env_config('LAST_COMMIT', default='1dcc9178c12efefc786bc653bacec50a1f79161b', cast=str)

    @property
    def NODE_NAME(self):
        return self.env_config('NODE_NAME', default='', cast=str)

    @property
    def NODE_EMAIL(self):
        return self.env_config('NODE_EMAIL', default='', cast=str)

    @property
    def NODE_DESCRIPTION(self):
        return self.env_config('NODE_DESCRIPTION', default='', cast=str)

    @property
    def AUTH_CHALLENGE_EXPIRED(self):
        return 3 * 60

    @property
    def ACCESS_TOKEN_EXPIRED(self):
        return 7 * 24 * 60 * 60

    @property
    def BACKUP_IS_SYNC(self):
        return self.env_config('BACKUP_IS_SYNC', default='False', cast=bool)


hive_setting = HiveSetting()
