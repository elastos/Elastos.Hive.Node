from src.modules.files.local_file import LocalFile


class FileCache:
    def __init__(self):
        pass

    @staticmethod
    def delete_files(user_did, cids: list):
        for cid in cids:
            file_path = LocalFile.get_cid_cache_dir(user_did) / cid
            if file_path.exists():
                file_path.unlink()

    @staticmethod
    def get_path(user_did, cid: str):
        return FileCache.get_path_by_cid(user_did, cid)

    @staticmethod
    def get_path_by_cid(user_did, cid: str):
        return LocalFile.get_cid_cache_dir(user_did, need_create=True) / cid

    @staticmethod
    def remove_file(user_did, cid: str):
        file = FileCache.get_path_by_cid(user_did, cid)
        if file.exists():
            file.unlink()
