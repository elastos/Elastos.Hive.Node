from src.modules.database.mongodb_client import MongodbClient
from src.utils.consts import COL_IPFS_CID_REF, CID, COUNT


class IpfsCidRef:
    def __init__(self, cid):
        """ This class represents the references of the cid in the files service. """
        self.cid = cid
        self.mcli = MongodbClient()

    def increase(self, count=1):
        """ directly increase count if exists, else set count """

        filter_ = {CID: self.cid}
        update = {
            '$inc': {COUNT: count},  # increase count when exists, else set to count
        }

        col = self.mcli.get_management_collection(COL_IPFS_CID_REF)
        col.update_one(filter_, update, upsert=True)

    def decrease(self, count=1):
        """ decrease count if not to zero, else to remove cid info """

        filter_ = {CID: self.cid}

        # check if exists
        col = self.mcli.get_management_collection(COL_IPFS_CID_REF)
        doc = col.find_one(filter_)
        if not doc:
            return

        # delete or decrease
        if doc[COUNT] <= count:
            col.delete_one(filter_)
        else:
            update = {'$inc': {COUNT: -count}}
            col.update_one(filter_, update)
