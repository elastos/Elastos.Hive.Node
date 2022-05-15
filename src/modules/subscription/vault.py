from src.modules.database.mongodb_client import MongodbClient
from src.utils.http_exception import InsufficientStorageException, VaultNotFoundException
from src.utils_v1.constants import VAULT_SERVICE_MAX_STORAGE, VAULT_SERVICE_FILE_USE_STORAGE, VAULT_SERVICE_DB_USE_STORAGE, VAULT_SERVICE_COL, VAULT_SERVICE_DID


class Vault:
    """ Represents a user vault """

    def __init__(self, doc):
        self.doc = doc

    def get_storage_gap(self):
        return int(self.doc[VAULT_SERVICE_MAX_STORAGE] - (self.doc[VAULT_SERVICE_FILE_USE_STORAGE] + self.doc[VAULT_SERVICE_DB_USE_STORAGE]))

    def is_storage_full(self):
        return self.get_storage_gap() <= 0

    def check_storage(self):
        if self.is_storage_full():
            raise InsufficientStorageException()


class VaultManager:
    """ VaultManager is for other modules as a common class. """

    def __init__(self):
        self.mcli = MongodbClient()

    def get_vault(self, user_did):
        """ Get the vault for user or raise not-found exception. """
        col = self.mcli.get_management_collection(VAULT_SERVICE_COL)

        doc = col.find_one({VAULT_SERVICE_DID: user_did})
        if not doc:
            raise VaultNotFoundException()
        return Vault(doc)
