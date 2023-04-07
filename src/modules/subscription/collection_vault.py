import shutil
from datetime import datetime

from src import PaymentConfig, hive_setting
from src.utils.http_exception import VaultNotFoundException, FileNotFoundException
from src.modules.files.file_cache import FileCache
from src.modules.database.mongodb_collection import mongodb_collection, CollectionName, MongodbCollection, \
    CollectionGenericField
from src.modules.files.collection_ipfs_cid_ref import CollectionIpfsCidRef
from src.modules.subscription.vault import Vault
from src.modules.files.collection_file_metadata import CollectionFileMetadata
from src.modules.auth.collection_application import CollectionApplication
from src.modules.database.mongodb_client import mcli
from src.modules.files.ipfs_client import IpfsClient


class VaultState:
    RUNNING = "running"  # read and write
    FROZE = "freeze"  # read, but not write
    REMOVED = "removed"  # soft unsubscribe


@mongodb_collection(CollectionName.VAULT_SERVICE, is_management=True, is_internal=True)
class CollectionVault(MongodbCollection):
    """ represents a vault service, all user data is in the vault. """

    # INFO: All fields are compatible with v1.
    USER_DID = 'did'  # compatible with v1
    MAX_STORAGE_SIZE = 'max_storage'  # unit: byte (MB on v1, checked by 1024 * 1024)
    FILE_USED_SIZE = 'file_use_storage'  # unit: byte
    DATABASE_USED_SIZE = 'db_use_storage'  # unit: byte
    MODIFIED = 'modify_time'  # updated time for the vault information
    STARTED = 'start_time'  # pricing plan start time
    EXPIRED = 'end_time'  # pricing plan end time
    PRICING_USING = 'pricing_using'
    STATE = CollectionGenericField.STATE  # Maybe not exists.
    LATEST_ACCESS = 'latest_access_time'  # Latest access for database, files, scripting.
    IS_UPGRADED = 'is_upgraded'  # True mean the vault is from promotion.

    def __init__(self, col):
        MongodbCollection.__init__(self, col, is_management=True)

    def get_all_vaults(self, raise_not_found=False):
        vaults = self.find_many({self.USER_DID: {'$exists': True}})
        if not vaults and raise_not_found:
            raise VaultNotFoundException()

        return list(map(lambda d: Vault(**d), vaults))

    def get_vault_count(self) -> int:
        return self.count({})

    def get_vault(self, user_did) -> Vault:
        """ Get the vault for user or raise not-found exception.

        This method is also used to check the existence of the vault

        example:

            vault_manager.get_vault(user_did).check_storage_full().check_write_permission()

        """

        vault = self._only_get_vault(user_did)

        # try to revert to free package plan
        return self._try_to_downgrade_to_free(user_did, vault)

    def get_vault_access_statistics(self, user_did):
        access_count, access_amount, access_last_time = 0, 0, -1
        try:
            vault = self._only_get_vault(user_did)
            access_last_time = vault.get_latest_access_time()
        except VaultNotFoundException as e:
            pass

        apps = mcli.get_col(CollectionApplication).get_apps(user_did)
        if apps:
            access_count = sum(list(map(lambda app: app.get('access_count', 0), apps)))
            access_amount = sum(list(map(lambda app: app.get('access_amount', 0), apps)))

        return {
            'access_count': access_count,
            'access_amount': access_amount,
            'access_last_time': access_last_time
        }

    def create_vault(self, user_did, price_plan: dict, is_upgraded=False) -> Vault:
        now = datetime.now().timestamp()  # seconds in UTC
        # end time is timestamp or -1 (no end time)
        end_time = -1 if price_plan['serviceDays'] == -1 else now + price_plan['serviceDays'] * 24 * 60 * 60

        filter_ = {self.USER_DID: user_did}
        update = {
            '$set': {  # For update and insert
                self.MODIFIED: now,
                self.STATE: VaultState.RUNNING
            },
            '$setOnInsert': {  # Only for insert
                self.MAX_STORAGE_SIZE: int(price_plan["maxStorage"]) * 1024 * 1024,
                self.FILE_USED_SIZE: 0,
                self.DATABASE_USED_SIZE: 0,
                self.IS_UPGRADED: is_upgraded,
                self.STARTED: now,
                self.EXPIRED: end_time,
                self.PRICING_USING: price_plan['name'],
                self.LATEST_ACCESS: -1,
            }
        }

        self.update_one(filter_, update, upsert=True)
        return self._only_get_vault(user_did)

    def upgrade_vault(self, user_did, plan: dict, vault: Vault = None):
        """ upgrade the vault to specific pricing plan """

        # Support vault = None to avoid recursive calling with 'get_vault()'
        if not vault:
            vault = self._only_get_vault(user_did)

        # Upgrading contains: vault max storage size, expired date, plan
        start, end = PaymentConfig.get_plan_period(vault.get_plan(), vault.get_end_time(), plan)
        filter_ = {self.USER_DID: user_did}
        update = {
            self.PRICING_USING: plan['name'],
            self.MAX_STORAGE_SIZE: int(plan["maxStorage"]) * 1024 * 1024,
            self.STARTED: start,
            self.EXPIRED: end,  # -1 means endless
            self.MODIFIED: int(datetime.now().timestamp()),
        }

        self.update_one(filter_, {'$set': update}, contains_extra=False)

    def remove_vault(self, user_did, force):
        self._drop_vault_data(user_did, force)

        filter_ = {self.USER_DID: user_did}
        if force:
            # remove applications.
            mcli.get_col(CollectionApplication).remove_user(user_did)

            # remove the vault.
            self.delete_one(filter_)
        else:
            self.update_one(filter_, {
                '$set': {
                    self.STATE: VaultState.REMOVED
                }
            })

    @staticmethod
    def remove_vault_app(user_did, app_did):
        # TODO: move to CollectionApplication
        app = mcli.get_col(CollectionApplication).get_app(user_did, app_did)
        if not app:
            return

        try:
            metadatas = mcli.get_col(CollectionFileMetadata, user_did=user_did, app_did=app_did).get_all_file_metadatas()
            # 1. Clean cache files.
            FileCache.delete_files(user_did, list(map(lambda md: md[CollectionFileMetadata.IPFS_CID], metadatas)))
            # 2. Unpin cids.
            ipfs_client = IpfsClient()
            for m in metadatas:
                if mcli.get_col(CollectionIpfsCidRef).decrease_cid_ref(m[CollectionFileMetadata.IPFS_CID]):
                    ipfs_client.cid_unpin(m[CollectionFileMetadata.IPFS_CID])
            # 3. Delete app database
            mcli.drop_user_database(user_did, app_did)
        except FileNotFoundException:
            # No files on the app.
            pass

        # Remove app information
        mcli.get_col(CollectionApplication).remove_user_app(user_did, app_did)

    def recalculate_vault_database_used_size(self, user_did: str):
        """ Update all databases used size in vault """
        # Get all application DIDs of user DID, then get their sizes.
        app_dids = mcli.get_col(CollectionApplication).get_app_dids(user_did)
        size = sum(list(map(lambda d: mcli.get_user_database_size(user_did, d), app_dids)))

        self.update_vault_database_used_size(user_did, size, is_reset=True)

    def update_vault_file_used_size(self, user_did, size: int, is_reset=False):
        self._update_vault_storage_used_size(user_did, size, True, is_reset=is_reset)

    def update_vault_database_used_size(self, user_did, size: int, is_reset=False):
        self._update_vault_storage_used_size(user_did, size, False, is_reset=is_reset)

    def update_vault_latest_access(self, user_did: str):
        filter_ = {self.USER_DID: user_did}
        update = {'$set': {self.LATEST_ACCESS: int(datetime.now().timestamp())}}

        self.update_one(filter_, update, contains_extra=False)

    def activate_vault(self, user_did, is_activate: bool):
        """ active or deactivate the vault without checking the existence of the vault """

        filter_ = {self.USER_DID: user_did}
        update = {'$set': {
            self.STATE: VaultState.RUNNING if is_activate else VaultState.FROZE,
            self.MODIFIED: int(datetime.now().timestamp())}}

        self.update_one(filter_, update, contains_extra=False)

    def _only_get_vault(self, user_did) -> Vault:
        """ common method to all other method in this class """
        doc = self.find_one({self.USER_DID: user_did})
        if not doc or doc.get(self.STATE, None) == VaultState.REMOVED:
            raise VaultNotFoundException()
        return Vault(**doc)

    def _try_to_downgrade_to_free(self, user_did, vault: Vault):
        if PaymentConfig.is_free_plan(vault.get_plan_name()):
            return vault

        if not vault.is_expired():
            return vault

        # downgrade now
        self.upgrade_vault(user_did, PaymentConfig.get_free_vault_plan(), vault=vault)
        return self._only_get_vault(user_did)

    def _drop_vault_data(self, user_did, force):
        """ drop all data belong to user, include files and databases.

        :param user_did: user did
        :param force: force to remove all data of the vault, else just remove the files cache.
        """

        # Remove local user's vault folder which contains files cache.
        path = hive_setting.get_user_vault_path(user_did)
        if path.exists():
            shutil.rmtree(path)

        if force:
            # remove all databases belong to user's vault
            app_dids = mcli.get_col(CollectionApplication).get_app_dids(user_did)
            for app_did in app_dids:
                mcli.drop_user_database(user_did, app_did)

    def _update_vault_storage_used_size(self, user_did, size, is_files: bool, is_reset=False):
        """ update files or databases usage of the vault

        :param user_did user DID
        :param size files&databases total size or increased size
        :param is_files files or databases storage usage
        :param is_reset: True means reset by size, else increase with size
        """

        if not is_reset and size == 0:
            return

        key = self.FILE_USED_SIZE if is_files else self.DATABASE_USED_SIZE

        filter_ = {self.USER_DID: user_did}

        now = int(datetime.now().timestamp())
        if is_reset:
            update = {'$set': {key: size, self.MODIFIED: now}}
        else:
            update = {
                '$inc': {key: size},
                '$set': {self.MODIFIED: now}
            }

        self.update_one(filter_, update, contains_extra=False)
