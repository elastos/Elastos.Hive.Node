from src.utils.consts import COL_IPFS_CID_REF, CID, COUNT
from src.utils.db_client import cli
from src.utils.file_manager import fm
from src.utils_v1.constants import DID_INFO_DB_NAME


class IpfsCidRef:
    def __init__(self, cid):
        """ This class represents the references of the cid in the files service. """
        self.cid = cid

    def __get_doc_by_cid(self):
        return cli.find_one_origin(DID_INFO_DB_NAME, COL_IPFS_CID_REF, {CID: self.cid},
                                   create_on_absence=True, throw_exception=False)

    def __update_refcount_cid(self, count):
        col_filter = {CID: self.cid}
        update = {'$set': {
            COUNT: count
        }}
        cli.update_one_origin(DID_INFO_DB_NAME, COL_IPFS_CID_REF, col_filter, update,
                              create_on_absence=True, is_extra=True)

    def increase(self, count=1):
        doc = self.__get_doc_by_cid()
        if not doc:
            doc = {
                CID: self.cid,
                COUNT: count
            }
            cli.insert_one_origin(DID_INFO_DB_NAME, COL_IPFS_CID_REF, doc, create_on_absence=True)
        else:
            self.__update_refcount_cid(doc[COUNT] + count)

    def decrease(self, count=1):
        doc = self.__get_doc_by_cid()
        if not doc:
            return
        if doc[COUNT] <= count:
            cli.delete_one_origin(DID_INFO_DB_NAME, COL_IPFS_CID_REF, {CID: self.cid}, is_check_exist=False)
            fm.ipfs_unpin_cid(self.cid)
        else:
            self.__update_refcount_cid(doc[COUNT] - count)
