import logging

from src.utils.consts import USR_DID, APP_DID, COL_IPFS_FILES_PATH, COL_IPFS_FILES, COL_IPFS_FILES_SHA256, COL_IPFS_FILES_IS_FILE, SIZE, \
    COL_IPFS_FILES_IPFS_CID, COL_IPFS_FILES_IS_ENCRYPT, COL_IPFS_FILES_ENCRYPT_METHOD
from src.utils.http_exception import FileNotFoundException
from src.modules.auth.user import UserManager
from src.modules.files.ipfs_cid_ref import IpfsCidRef
from src.modules.database.mongodb_client import MongodbClient, Dotdict


class FileMetadata(Dotdict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class FileMetadataManager:
    def __init__(self):
        self.mcli = MongodbClient()
        self.user_manager = UserManager()

    def __get_col(self, user_did, app_did):
        return self.mcli.get_user_collection(user_did, app_did, COL_IPFS_FILES, create_on_absence=True)

    def get_all_metadatas(self, user_did, app_did, folder_dir: str = None):
        """ Get files metadata under folder 'path'. Get all application files if folder_dir not specified.

        raise FileNotFoundException if no files under sub-folder which means sub-folder does not exist.
        """

        filter_ = {USR_DID: user_did, APP_DID: app_did}
        if folder_dir:
            # if specify the path, it will find the files start with folder name
            folder_path = folder_dir if folder_dir[len(folder_dir) - 1] == '/' else f'{folder_dir}/'
            filter_[COL_IPFS_FILES_PATH] = {
                '$regex': f'^{folder_path}'
            }

        docs = self.__get_col(user_did, app_did).find_many(filter_)
        if not docs and folder_dir:
            # root path always exists
            raise FileNotFoundException(f'The directory {folder_dir} does not exist.')

        return list(map(lambda d: FileMetadata(**d), docs))

    def get_metadata(self, user_did, app_did, rel_path):
        filter_ = {USR_DID: user_did, APP_DID: app_did, COL_IPFS_FILES_PATH: rel_path}
        doc = self.__get_col(user_did, app_did).find_one(filter_)
        if not doc:
            raise FileNotFoundException(f'The file {rel_path} does not exist.')

        return FileMetadata(**doc)

    def add_metadata(self, user_did, app_did, rel_path: str, sha256: str, size: int, cid: str, is_encrypt: bool, encrypt_method: str):
        """ add or update the file metadata """
        filter_ = {USR_DID: user_did, APP_DID: app_did, COL_IPFS_FILES_PATH: rel_path}
        update = {'$set': {
            COL_IPFS_FILES_SHA256: sha256,
            COL_IPFS_FILES_IS_FILE: True,
            SIZE: size,
            COL_IPFS_FILES_IPFS_CID: cid,
            COL_IPFS_FILES_IS_ENCRYPT: is_encrypt,  # added from v2.9
            COL_IPFS_FILES_ENCRYPT_METHOD: encrypt_method,  # added from v2.9
        }}
        self.__get_col(user_did, app_did).update_one(filter_, update, upsert=True)

        return self.get_metadata(user_did, app_did, rel_path)

    def move_metadata(self, user_did, app_did, src_path: str, dst_path: str):
        filter_ = {USR_DID: user_did, APP_DID: app_did, COL_IPFS_FILES_PATH: src_path}
        update = {'$set': {COL_IPFS_FILES_PATH: dst_path}}
        self.__get_col(user_did, app_did).update_one(filter_, update)

    def delete_metadata(self, user_did, app_did, rel_path, cid):
        filter_ = {USR_DID: user_did, APP_DID: app_did, COL_IPFS_FILES_PATH: rel_path}
        result = self.__get_col(user_did, app_did).delete_one(filter_)
        if result['deleted_count'] > 0 and cid:
            IpfsCidRef(cid).decrease()

    def get_backup_file_metadatas(self, user_did):
        """ get all cid infos from user's vault for backup

        The result shows the files content (cid) information.
        """

        app_dids, total_size, cids = self.user_manager.get_apps(user_did), 0, list()

        def get_cid_metadata_from_list(cid_mts, file_mt):
            if not cid_mts:
                return None
            for mt in cid_mts:
                if mt['cid'] == file_mt[COL_IPFS_FILES_IPFS_CID]:
                    if mt['sha256'] != file_mt[COL_IPFS_FILES_SHA256] or mt['size'] != int(file_mt[SIZE]):
                        logging.error(f'Found an unexpected file {file_mt[COL_IPFS_FILES_PATH]} with same CID, '
                                      f'but different sha256 or size.')
                    return mt
            return None

        for app_did in app_dids:
            metadatas = self.get_all_metadatas(user_did, app_did)
            for doc in metadatas:
                mt = get_cid_metadata_from_list(cids, doc)
                if mt:
                    mt['count'] += 1
                else:
                    cids.append({'cid': doc[COL_IPFS_FILES_IPFS_CID],
                                 'sha256': doc[COL_IPFS_FILES_SHA256],
                                 'size': int(doc[SIZE]),
                                 'count': 1})
            total_size += sum([doc[SIZE] for doc in metadatas])

        return total_size, cids
