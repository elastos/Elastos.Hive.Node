from src.modules.files.local_file import LocalFile
from src.utils.consts import COL_IPFS_FILES_IPFS_CID


class FileCacheService:
    def __init__(self):
        pass

    @staticmethod
    def delete_cache_files(user_did, metadatas: list):
        for m in metadatas:
            file_path = LocalFile.get_cid_cache_dir(user_did) / m[COL_IPFS_FILES_IPFS_CID]
            if file_path.exists():
                file_path.unlink()
