import logging

from src.utils.http_exception import FileNotFoundException
from src.modules.files.file_cache import FileCache
from src.modules.database.mongodb_collection import MongodbCollection, mongodb_collection, CollectionName, \
    CollectionGenericField
from src.modules.files.collection_ipfs_cid_ref import CollectionIpfsCidRef
from src.modules.database.mongodb_client import mcli


@mongodb_collection(CollectionName.FILE_METADATA, is_management=False, is_internal=True)
class CollectionFileMetadata(MongodbCollection):
    USR_DID = CollectionGenericField.USR_DID
    APP_DID = CollectionGenericField.APP_DID
    PATH = 'path'
    SHA256 = 'sha256'
    SIZE = CollectionGenericField.SIZE
    IS_FILE = 'is_file'
    IPFS_CID = 'ipfs_cid'
    IS_ENCRYPT = 'is_encrypt'
    ENCRYPT_METHOD = 'encrypt_method'

    def __init__(self, col):
        MongodbCollection.__init__(self, col, is_management=False)

    def get_all_file_metadatas(self, folder_dir: str = None):
        """ Get files metadata under folder 'path'. Get all application files if folder_dir not specified.

        raise FileNotFoundException if no files under sub-folder which means sub-folder does not exist.
        """

        filter_ = self._get_internal_filter()
        if folder_dir:
            # if specify the path, it will find the files start with folder name
            folder_path = folder_dir if folder_dir[len(folder_dir) - 1] == '/' else f'{folder_dir}/'
            filter_[self.PATH] = {
                '$regex': f'^{folder_path}'
            }

        docs = self.find_many(filter_)
        if not docs and folder_dir:
            # root path always exists
            raise FileNotFoundException(f'The directory {folder_dir} does not exist.')

        return docs

    def get_file_metadata(self, rel_path):
        doc = self.find_one(self._get_internal_filter(rel_path))
        if not doc:
            raise FileNotFoundException(f'The file {rel_path} does not exist.')

        return doc

    def upsert_file_metadata(self, rel_path: str, sha256: str, size: int, cid: str, is_encrypt: bool, encrypt_method: str):
        """ add or update the file metadata """
        update = {'$set': {
            self.SHA256: sha256,
            self.IS_FILE: True,
            self.SIZE: size,
            self.IPFS_CID: cid,
            self.IS_ENCRYPT: is_encrypt,  # added from v2.9
            self.ENCRYPT_METHOD: encrypt_method,  # added from v2.9
        }}
        self.update_one(self._get_internal_filter(rel_path), update, upsert=True)

        return self.get_file_metadata(rel_path)

    def move_file_metadata(self, src_path: str, dst_path: str):
        update = {'$set': {self.PATH: dst_path}}
        self.update_one(self._get_internal_filter(src_path), update)

    def delete_file_metadata(self, rel_path, cid):
        result = self.delete_one(self._get_internal_filter(rel_path))
        if result['deleted_count'] > 0 and cid:
            removed = mcli.get_col(CollectionIpfsCidRef).decrease_cid_ref(cid)
            if removed:
                FileCache.remove_file(self.user_did, cid)

    def _get_internal_filter(self, path=None):
        filter_ = {self.USR_DID: self.user_did, self.APP_DID: self.app_did}
        if path is not None:
            filter_[self.PATH] = path
        return filter_

    @classmethod
    def get_backup_file_metadatas(cls, user_did):
        """ get all cid infos from user's vault for backup
        # TODO: move this to CollectionVault and split it into CollectionApplication.
        The result shows the files content (cid) information.
        """
        from src.modules.auth.collection_application import CollectionApplication
        app_dids, total_size, cids = mcli.get_col(CollectionApplication).get_app_dids(user_did), 0, list()

        def get_cid_metadata_from_list(cid_mts, file_mt):
            if not cid_mts:
                return None
            for mt in cid_mts:
                if mt['cid'] == file_mt[cls.IPFS_CID]:
                    if mt['sha256'] != file_mt[cls.SHA256] or mt['size'] != int(file_mt[cls.SIZE]):
                        logging.error(f'Found an unexpected file {file_mt[cls.PATH]} with same CID, '
                                      f'but different sha256 or size.')
                    return mt
            return None

        for app_did in app_dids:
            metadatas = mcli.get_col(CollectionFileMetadata, user_did=user_did, app_did=app_did).get_all_file_metadatas()
            for doc in metadatas:
                mt = get_cid_metadata_from_list(cids, doc)
                if mt:
                    mt['count'] += 1
                else:
                    cids.append({'cid': doc[cls.IPFS_CID],
                                 'sha256': doc[cls.SHA256],
                                 'size': int(doc[cls.SIZE]),
                                 'count': 1})
            total_size += sum([doc[cls.SIZE] for doc in metadatas])

        return total_size, cids
