from src.utils.consts import USR_DID, APP_DID, COL_IPFS_FILES_PATH, COL_IPFS_FILES
from src.utils.http_exception import FileNotFoundException
from src.modules.files.ipfs_cid_ref import IpfsCidRef
from src.modules.database.mongodb_client import MongodbClient, Dotdict


class FileMetadata(Dotdict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class FileMetadataManager:
    def __init__(self):
        self.mcli = MongodbClient()

    def __get_col(self, user_did, app_did):
        return self.mcli.get_user_collection(user_did, app_did, COL_IPFS_FILES, create_on_absence=True)

    def get_metadata(self, user_did, app_did, path):
        filter_ = {USR_DID: user_did, APP_DID: app_did, COL_IPFS_FILES_PATH: path}
        doc = self.__get_col(user_did, app_did).find_one(filter_)
        if not doc:
            raise FileNotFoundException(f'The file {path} does not exist.')

        return FileMetadata(**doc)

    def delete_metadata(self, user_did, app_did, path, cid):
        filter_ = {USR_DID: user_did, APP_DID: app_did, COL_IPFS_FILES_PATH: path}
        result = self.__get_col(user_did, app_did).delete_one(filter_)
        if result['deleted_count'] > 0 and cid:
            IpfsCidRef(cid).decrease()
