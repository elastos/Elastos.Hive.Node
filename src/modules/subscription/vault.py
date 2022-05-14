from src.modules.database.mongodb_client import MongodbClient
from src.utils.file_manager import fm
from src.utils.http_exception import InsufficientStorageException, VaultNotFoundException


class Vault:
    """ Vault operation like get information. """

    def __init__(self, user_did):
        self.user_did = user_did
        self.mcli = MongodbClient()
        self.fm = fm

    def get_storage_gap(self):
        return self.fm.get_vault_max_size(self.user_did) - self.fm.get_vault_storage_size(self.user_did)

    def is_storage_full(self):
        return self.get_storage_gap() > 0

    def check_vault(self, check_vault=True, check_storage=False):
        """ Check vault exits and storage is enough

        :param check_vault if check the vault exists.
        :param check_storage if check the storage.
        """
        if check_vault and not self.mcli.get_vault_info(self.user_did):
            raise VaultNotFoundException()

        # Simplify handle this. Just check if current is enough.
        if check_storage and self.is_storage_full():
            raise InsufficientStorageException()
